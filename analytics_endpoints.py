"""
Analytics Endpoints for KLA Konnect API
Add these endpoints to your main.py file
"""

from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, func, and_, or_, case, extract
from sqlalchemy.sql import text
import math
from collections import defaultdict

# ==================== ANALYTICS ENDPOINTS ====================

@app.get("/analytics/incidents/overview", tags=["analytics"])
async def get_incidents_overview(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_city_reports: bool = Query(False, description="Include city reports")
):
    """
    Get comprehensive incident overview with counts, trends, and status breakdown
    """
    # Build base query
    base_filter = []
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Total counts by status
    status_query = select(
        incidents_table.c.status,
        func.count(incidents_table.c.id).label("count")
    ).group_by(incidents_table.c.status)
    
    if base_filter:
        status_query = status_query.where(and_(*base_filter))
    
    status_results = await database.fetch_all(status_query)
    
    status_mapping = {
        "0": "archived",
        "1": "published", 
        "2": "resolved",
        "3": "rejected"
    }
    
    status_breakdown = {
        "archived": 0,
        "published": 0,
        "resolved": 0,
        "rejected": 0,
        "total": 0
    }
    
    for row in status_results:
        status_key = status_mapping.get(str(row["status"]), "unknown")
        count = int(row["count"])
        status_breakdown[status_key] = count
        status_breakdown["total"] += count
    
    # Emergency incidents
    emergency_query = select(
        func.count(incidents_table.c.id)
    ).where(incidents_table.c.isemergency == True)
    
    if base_filter:
        emergency_query = emergency_query.where(and_(*base_filter))
    
    emergency_count = await database.fetch_one(emergency_query)
    
    # Average resolution time (for resolved incidents)
    resolution_query = select(
        func.avg(
            func.extract('epoch', incidents_table.c.dateupdated - incidents_table.c.datecreated) / 3600
        ).label("avg_hours")
    ).where(incidents_table.c.status == "2")
    
    if base_filter:
        resolution_query = resolution_query.where(and_(*base_filter))
    
    avg_resolution = await database.fetch_one(resolution_query)
    avg_resolution_hours = float(avg_resolution["avg_hours"]) if avg_resolution["avg_hours"] else 0
    
    # Daily trend (last 30 days or within date range)
    if not start_date:
        trend_start = datetime.now() - timedelta(days=30)
    else:
        trend_start = datetime.strptime(start_date, "%Y-%m-%d")
    
    trend_query = select(
        func.date(incidents_table.c.datecreated).label("date"),
        func.count(incidents_table.c.id).label("count")
    ).where(incidents_table.c.datecreated >= trend_start).group_by(
        func.date(incidents_table.c.datecreated)
    ).order_by(func.date(incidents_table.c.datecreated))
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        trend_query = trend_query.where(incidents_table.c.datecreated < end_dt)
    
    if not include_city_reports:
        trend_query = trend_query.where(incidents_table.c.iscityreport == False)
    
    trend_results = await database.fetch_all(trend_query)
    
    daily_trend = [
        {
            "date": str(row["date"]),
            "count": int(row["count"])
        }
        for row in trend_results
    ]
    
    return {
        "status_breakdown": status_breakdown,
        "emergency_incidents": int(emergency_count[0]) if emergency_count else 0,
        "avg_resolution_hours": round(avg_resolution_hours, 2),
        "daily_trend": daily_trend,
        "date_range": {
            "start": start_date or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": end_date or datetime.now().strftime("%Y-%m-%d")
        }
    }


@app.get("/analytics/incidents/by-category", tags=["analytics"])
async def get_incidents_by_category(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    include_city_reports: bool = Query(False),
    top_n: int = Query(10, ge=1, le=50, description="Number of top categories to return")
):
    """
    Get incident distribution by category with detailed breakdown
    """
    j = incidents_table.join(
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )
    
    base_filter = []
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Category breakdown with status counts
    query = select(
        incidentcategories_table.c.id.label("category_id"),
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.image.label("category_image"),
        func.count(incidents_table.c.id).label("total_count"),
        func.sum(case((incidents_table.c.status == "1", 1), else_=0)).label("published"),
        func.sum(case((incidents_table.c.status == "2", 1), else_=0)).label("resolved"),
        func.sum(case((incidents_table.c.status == "3", 1), else_=0)).label("rejected"),
        func.sum(case((incidents_table.c.isemergency == True, 1), else_=0)).label("emergency"),
        func.avg(incidents_table.c.upvotes).label("avg_upvotes")
    ).select_from(j).group_by(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name,
        incidentcategories_table.c.image
    ).order_by(func.count(incidents_table.c.id).desc()).limit(top_n)
    
    if base_filter:
        query = query.where(and_(*base_filter))
    
    results = await database.fetch_all(query)
    
    categories = []
    total_incidents = 0
    
    for row in results:
        count = int(row["total_count"])
        total_incidents += count
        
        categories.append({
            "category_id": row["category_id"],
            "category_name": row["category_name"],
            "category_image": row["category_image"],
            "total_count": count,
            "published": int(row["published"] or 0),
            "resolved": int(row["resolved"] or 0),
            "rejected": int(row["rejected"] or 0),
            "emergency": int(row["emergency"] or 0),
            "avg_upvotes": round(float(row["avg_upvotes"] or 0), 2),
            "percentage": 0  # Will calculate after getting total
        })
    
    # Calculate percentages
    for cat in categories:
        if total_incidents > 0:
            cat["percentage"] = round((cat["total_count"] / total_incidents) * 100, 2)
    
    return {
        "categories": categories,
        "total_incidents": total_incidents,
        "total_categories": len(categories)
    }


@app.get("/analytics/incidents/hotspots", tags=["analytics"])
async def get_incident_hotspots(
    radius_meters: float = Query(500, ge=100, le=5000, description="Radius in meters for clustering"),
    min_incidents: int = Query(3, ge=2, le=20, description="Minimum incidents to qualify as hotspot"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    include_city_reports: bool = Query(False),
    top_n: int = Query(10, ge=1, le=50)
):
    """
    Identify geographic hotspots where incidents cluster within specified radius
    Uses grid-based clustering for performance
    """
    base_filter = [
        incidents_table.c.addresslat.isnot(None),
        incidents_table.c.addresslong.isnot(None)
    ]
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if category_id:
        base_filter.append(incidents_table.c.incidentcategoryid == category_id)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Fetch all incidents with coordinates
    query = select(
        incidents_table.c.id,
        incidents_table.c.name,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.address,
        incidents_table.c.incidentcategoryid,
        incidents_table.c.status,
        incidents_table.c.datecreated
    ).where(and_(*base_filter))
    
    incidents = await database.fetch_all(query)
    
    if not incidents:
        return {
            "hotspots": [],
            "total_hotspots": 0,
            "parameters": {
                "radius_meters": radius_meters,
                "min_incidents": min_incidents
            }
        }
    
    # Haversine distance function
    def haversine_distance(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlambda = math.radians(float(lon2) - float(lon1))
        
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    # Simple grid-based clustering
    # Convert incidents to list for processing
    incident_list = [dict(inc) for inc in incidents]
    processed = set()
    hotspots = []
    
    for i, incident in enumerate(incident_list):
        if i in processed:
            continue
        
        lat1 = float(incident["addresslat"])
        lon1 = float(incident["addresslong"])
        
        # Find all incidents within radius
        cluster = [incident]
        cluster_indices = {i}
        
        for j, other in enumerate(incident_list):
            if j in processed or j == i:
                continue
            
            lat2 = float(other["addresslat"])
            lon2 = float(other["addresslong"])
            
            distance = haversine_distance(lat1, lon1, lat2, lon2)
            
            if distance <= radius_meters:
                cluster.append(other)
                cluster_indices.add(j)
        
        # If cluster meets minimum size, it's a hotspot
        if len(cluster) >= min_incidents:
            # Calculate centroid
            avg_lat = sum(float(inc["addresslat"]) for inc in cluster) / len(cluster)
            avg_lon = sum(float(inc["addresslong"]) for inc in cluster) / len(cluster)
            
            # Get status breakdown
            status_counts = defaultdict(int)
            category_counts = defaultdict(int)
            
            for inc in cluster:
                status_counts[inc["status"]] += 1
                if inc["incidentcategoryid"]:
                    category_counts[inc["incidentcategoryid"]] += 1
            
            # Get most common address (for naming)
            addresses = [inc["address"] for inc in cluster if inc["address"]]
            most_common_address = max(set(addresses), key=addresses.count) if addresses else "Unknown Location"
            
            hotspots.append({
                "center_lat": round(avg_lat, 6),
                "center_long": round(avg_lon, 6),
                "incident_count": len(cluster),
                "location_name": most_common_address,
                "radius_meters": radius_meters,
                "status_breakdown": dict(status_counts),
                "top_category_id": max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None,
                "incident_ids": [inc["id"] for inc in cluster]
            })
            
            # Mark as processed
            processed.update(cluster_indices)
    
    # Sort by incident count
    hotspots.sort(key=lambda x: x["incident_count"], reverse=True)
    
    # Limit to top N
    hotspots = hotspots[:top_n]
    
    # Enrich with category names
    for hotspot in hotspots:
        if hotspot["top_category_id"]:
            cat_query = select(incidentcategories_table.c.name).where(
                incidentcategories_table.c.id == hotspot["top_category_id"]
            )
            cat_result = await database.fetch_one(cat_query)
            hotspot["top_category_name"] = cat_result["name"] if cat_result else "Unknown"
        else:
            hotspot["top_category_name"] = None
    
    return {
        "hotspots": hotspots,
        "total_hotspots": len(hotspots),
        "parameters": {
            "radius_meters": radius_meters,
            "min_incidents": min_incidents,
            "top_n": top_n
        }
    }


@app.get("/analytics/users/activity", tags=["analytics"])
async def get_user_activity_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None, description="citizen, clerk, engineer, admin")
):
    """
    Get user activity statistics including registrations, active users, and incident submissions
    """
    base_filter = []
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(users_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(users_table.c.datecreated < end_dt)
    
    # User type filter
    type_filter = None
    if user_type:
        if user_type == "citizen":
            type_filter = users_table.c.iscitizen == True
        elif user_type == "clerk":
            type_filter = users_table.c.isclerk == True
        elif user_type == "engineer":
            type_filter = users_table.c.isengineer == True
        elif user_type == "admin":
            type_filter = users_table.c.isadmin == True
    
    if type_filter is not None:
        base_filter.append(type_filter)
    
    # Total users
    total_query = select(func.count(users_table.c.id))
    if base_filter:
        total_query = total_query.where(and_(*base_filter))
    
    total_users = await database.fetch_one(total_query)
    
    # Active users (status = 1)
    active_query = select(func.count(users_table.c.id)).where(
        users_table.c.status == "1"
    )
    if base_filter:
        active_query = active_query.where(and_(*base_filter))
    
    active_users = await database.fetch_one(active_query)
    
    # User registrations over time
    reg_query = select(
        func.date(users_table.c.datecreated).label("date"),
        func.count(users_table.c.id).label("count")
    ).group_by(func.date(users_table.c.datecreated)).order_by(
        func.date(users_table.c.datecreated)
    )
    
    if base_filter:
        reg_query = reg_query.where(and_(*base_filter))
    
    registrations = await database.fetch_all(reg_query)
    
    # Top contributors (users with most incidents)
    contributor_query = select(
        users_table.c.id,
        users_table.c.firstname,
        users_table.c.lastname,
        users_table.c.email,
        func.count(incidents_table.c.id).label("incident_count")
    ).select_from(
        users_table.join(incidents_table, users_table.c.id == incidents_table.c.createdby)
    ).group_by(
        users_table.c.id,
        users_table.c.firstname,
        users_table.c.lastname,
        users_table.c.email
    ).order_by(func.count(incidents_table.c.id).desc()).limit(10)
    
    contributors = await database.fetch_all(contributor_query)
    
    return {
        "total_users": int(total_users[0]) if total_users else 0,
        "active_users": int(active_users[0]) if active_users else 0,
        "registration_trend": [
            {
                "date": str(row["date"]),
                "count": int(row["count"])
            }
            for row in registrations
        ],
        "top_contributors": [
            {
                "user_id": row["id"],
                "name": f"{row['firstname']} {row['lastname']}",
                "email": row["email"],
                "incident_count": int(row["incident_count"])
            }
            for row in contributors
        ]
    }


@app.get("/analytics/incidents/time-series", tags=["analytics"])
async def get_incidents_time_series(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    granularity: str = Query("day", description="day, week, month, year"),
    category_id: Optional[str] = Query(None),
    include_city_reports: bool = Query(False)
):
    """
    Get time-series data for incidents with configurable granularity
    """
    base_filter = []
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if category_id:
        base_filter.append(incidents_table.c.incidentcategoryid == category_id)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Build query based on granularity
    if granularity == "day":
        time_expr = func.date(incidents_table.c.datecreated)
    elif granularity == "week":
        time_expr = func.date_trunc('week', incidents_table.c.datecreated)
    elif granularity == "month":
        time_expr = func.date_trunc('month', incidents_table.c.datecreated)
    elif granularity == "year":
        time_expr = func.date_trunc('year', incidents_table.c.datecreated)
    else:
        time_expr = func.date(incidents_table.c.datecreated)
    
    query = select(
        time_expr.label("period"),
        func.count(incidents_table.c.id).label("total"),
        func.sum(case((incidents_table.c.status == "1", 1), else_=0)).label("published"),
        func.sum(case((incidents_table.c.status == "2", 1), else_=0)).label("resolved"),
        func.sum(case((incidents_table.c.status == "3", 1), else_=0)).label("rejected"),
        func.sum(case((incidents_table.c.isemergency == True, 1), else_=0)).label("emergency")
    ).group_by("period").order_by("period")
    
    if base_filter:
        query = query.where(and_(*base_filter))
    
    results = await database.fetch_all(query)
    
    return {
        "granularity": granularity,
        "data": [
            {
                "period": str(row["period"]),
                "total": int(row["total"]),
                "published": int(row["published"] or 0),
                "resolved": int(row["resolved"] or 0),
                "rejected": int(row["rejected"] or 0),
                "emergency": int(row["emergency"] or 0)
            }
            for row in results
        ]
    }


@app.get("/analytics/incidents/resolution-time", tags=["analytics"])
async def get_resolution_time_analysis(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None)
):
    """
    Analyze incident resolution times by category
    """
    base_filter = [
        incidents_table.c.status == "2",  # Only resolved incidents
        incidents_table.c.dateupdated.isnot(None)
    ]
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if category_id:
        base_filter.append(incidents_table.c.incidentcategoryid == category_id)
    
    j = incidents_table.join(
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )
    
    # Resolution time in hours
    resolution_time_expr = func.extract(
        'epoch', 
        incidents_table.c.dateupdated - incidents_table.c.datecreated
    ) / 3600
    
    query = select(
        incidentcategories_table.c.id.label("category_id"),
        incidentcategories_table.c.name.label("category_name"),
        func.count(incidents_table.c.id).label("resolved_count"),
        func.avg(resolution_time_expr).label("avg_hours"),
        func.min(resolution_time_expr).label("min_hours"),
        func.max(resolution_time_expr).label("max_hours"),
        func.percentile_cont(0.5).within_group(resolution_time_expr).label("median_hours")
    ).select_from(j).where(and_(*base_filter)).group_by(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name
    ).order_by(func.avg(resolution_time_expr))
    
    results = await database.fetch_all(query)
    
    return {
        "by_category": [
            {
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "resolved_count": int(row["resolved_count"]),
                "avg_hours": round(float(row["avg_hours"] or 0), 2),
                "min_hours": round(float(row["min_hours"] or 0), 2),
                "max_hours": round(float(row["max_hours"] or 0), 2),
                "median_hours": round(float(row["median_hours"] or 0), 2),
                "avg_days": round(float(row["avg_hours"] or 0) / 24, 2)
            }
            for row in results
        ]
    }


@app.get("/analytics/reports/summary", tags=["analytics"])
async def get_comprehensive_report_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Generate a comprehensive summary report combining multiple metrics
    """
    # Use existing endpoints to build comprehensive report
    incidents_overview = await get_incidents_overview(start_date, end_date, False)
    category_breakdown = await get_incidents_by_category(start_date, end_date, False, 10)
    hotspots = await get_incident_hotspots(500, 3, start_date, end_date, None, False, 5)
    user_activity = await get_user_activity_stats(start_date, end_date, None)
    
    return {
        "period": {
            "start": start_date or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": end_date or datetime.now().strftime("%Y-%m-%d")
        },
        "incidents_overview": incidents_overview,
        "top_categories": category_breakdown,
        "top_hotspots": hotspots["hotspots"][:5],
        "user_activity": user_activity,
        "generated_at": datetime.now().isoformat()
    }
