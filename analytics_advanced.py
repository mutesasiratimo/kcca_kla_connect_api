"""
Additional Analytics & Export Endpoints
Add these to complement the main analytics endpoints
"""

from fastapi.responses import StreamingResponse
import io
import csv
import json

# ==================== EXPORT ENDPOINTS ====================

@app.get("/analytics/export/incidents-csv", tags=["analytics/export"])
async def export_incidents_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    include_city_reports: bool = Query(False)
):
    """
    Export incidents data as CSV
    """
    base_filter = []
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if status:
        base_filter.append(incidents_table.c.status == status)
    
    if category_id:
        base_filter.append(incidents_table.c.incidentcategoryid == category_id)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Join with categories and users
    j = incidents_table.join(
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    ).join(
        users_table,
        incidents_table.c.createdby == users_table.c.id
    )
    
    query = select(
        incidents_table.c.id,
        incidents_table.c.name,
        incidents_table.c.description,
        incidentcategories_table.c.name.label("category"),
        incidents_table.c.address,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.isemergency,
        incidents_table.c.status,
        incidents_table.c.upvotes,
        incidents_table.c.datecreated,
        incidents_table.c.dateupdated,
        users_table.c.email.label("reporter_email"),
        func.concat(users_table.c.firstname, ' ', users_table.c.lastname).label("reporter_name")
    ).select_from(j)
    
    if base_filter:
        query = query.where(and_(*base_filter))
    
    query = query.order_by(incidents_table.c.datecreated.desc())
    
    results = await database.fetch_all(query)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'ID', 'Name', 'Description', 'Category', 'Address', 'Latitude', 'Longitude',
        'Is Emergency', 'Status', 'Upvotes', 'Created Date', 'Updated Date',
        'Reporter Email', 'Reporter Name'
    ])
    
    writer.writeheader()
    
    status_map = {"0": "Archived", "1": "Published", "2": "Resolved", "3": "Rejected"}
    
    for row in results:
        writer.writerow({
            'ID': row['id'],
            'Name': row['name'],
            'Description': row['description'],
            'Category': row['category'],
            'Address': row['address'],
            'Latitude': row['addresslat'],
            'Longitude': row['addresslong'],
            'Is Emergency': 'Yes' if row['isemergency'] else 'No',
            'Status': status_map.get(row['status'], row['status']),
            'Upvotes': row['upvotes'] or 0,
            'Created Date': row['datecreated'].isoformat() if row['datecreated'] else '',
            'Updated Date': row['dateupdated'].isoformat() if row['dateupdated'] else '',
            'Reporter Email': row['reporter_email'],
            'Reporter Name': row['reporter_name']
        })
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=incidents_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@app.get("/analytics/geographic/distribution", tags=["analytics"])
async def get_geographic_distribution(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    grid_size_km: float = Query(1.0, ge=0.1, le=10.0, description="Grid cell size in kilometers")
):
    """
    Get geographic distribution of incidents using a grid system
    Returns incident density by geographic area
    """
    base_filter = [
        incidents_table.c.addresslat.isnot(None),
        incidents_table.c.addresslong.isnot(None),
        incidents_table.c.iscityreport == False
    ]
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    # Fetch all incidents
    query = select(
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.id
    ).where(and_(*base_filter))
    
    results = await database.fetch_all(query)
    
    # Grid size in degrees (approximate)
    # 1 degree latitude ≈ 111 km
    grid_size_deg = grid_size_km / 111.0
    
    # Group incidents into grid cells
    grid = defaultdict(list)
    
    for row in results:
        lat = float(row['addresslat'])
        lon = float(row['addresslong'])
        
        # Snap to grid
        grid_lat = round(lat / grid_size_deg) * grid_size_deg
        grid_lon = round(lon / grid_size_deg) * grid_size_deg
        
        grid[(grid_lat, grid_lon)].append(row['id'])
    
    # Convert to output format
    grid_cells = [
        {
            "center_lat": round(lat, 6),
            "center_long": round(lon, 6),
            "incident_count": len(incident_ids),
            "incident_ids": incident_ids,
            "density_score": len(incident_ids)  # Can be normalized if needed
        }
        for (lat, lon), incident_ids in grid.items()
    ]
    
    # Sort by density
    grid_cells.sort(key=lambda x: x['incident_count'], reverse=True)
    
    return {
        "grid_cells": grid_cells,
        "total_cells": len(grid_cells),
        "grid_size_km": grid_size_km,
        "total_incidents": len(results)
    }


@app.get("/analytics/incidents/comparison", tags=["analytics"])
async def compare_time_periods(
    period1_start: str = Query(..., description="First period start date (YYYY-MM-DD)"),
    period1_end: str = Query(..., description="First period end date (YYYY-MM-DD)"),
    period2_start: str = Query(..., description="Second period start date (YYYY-MM-DD)"),
    period2_end: str = Query(..., description="Second period end date (YYYY-MM-DD)")
):
    """
    Compare incident metrics between two time periods
    """
    async def get_period_stats(start_date: str, end_date: str):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        
        base_filter = [
            incidents_table.c.datecreated >= start_dt,
            incidents_table.c.datecreated < end_dt,
            incidents_table.c.iscityreport == False
        ]
        
        # Total incidents
        total_query = select(func.count(incidents_table.c.id)).where(and_(*base_filter))
        total = await database.fetch_one(total_query)
        
        # By status
        status_query = select(
            incidents_table.c.status,
            func.count(incidents_table.c.id).label("count")
        ).where(and_(*base_filter)).group_by(incidents_table.c.status)
        
        status_results = await database.fetch_all(status_query)
        status_breakdown = {row['status']: int(row['count']) for row in status_results}
        
        # Emergency count
        emergency_query = select(
            func.count(incidents_table.c.id)
        ).where(and_(*base_filter, incidents_table.c.isemergency == True))
        emergency = await database.fetch_one(emergency_query)
        
        # Top category
        j = incidents_table.join(
            incidentcategories_table,
            incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
        )
        
        category_query = select(
            incidentcategories_table.c.name,
            func.count(incidents_table.c.id).label("count")
        ).select_from(j).where(and_(*base_filter)).group_by(
            incidentcategories_table.c.name
        ).order_by(func.count(incidents_table.c.id).desc()).limit(1)
        
        top_category = await database.fetch_one(category_query)
        
        return {
            "total_incidents": int(total[0]) if total else 0,
            "status_breakdown": status_breakdown,
            "emergency_incidents": int(emergency[0]) if emergency else 0,
            "top_category": {
                "name": top_category['name'] if top_category else None,
                "count": int(top_category['count']) if top_category else 0
            }
        }
    
    period1_stats = await get_period_stats(period1_start, period1_end)
    period2_stats = await get_period_stats(period2_start, period2_end)
    
    # Calculate changes
    total_change = period2_stats['total_incidents'] - period1_stats['total_incidents']
    total_change_pct = (total_change / period1_stats['total_incidents'] * 100) if period1_stats['total_incidents'] > 0 else 0
    
    emergency_change = period2_stats['emergency_incidents'] - period1_stats['emergency_incidents']
    emergency_change_pct = (emergency_change / period1_stats['emergency_incidents'] * 100) if period1_stats['emergency_incidents'] > 0 else 0
    
    return {
        "period1": {
            "start": period1_start,
            "end": period1_end,
            "stats": period1_stats
        },
        "period2": {
            "start": period2_start,
            "end": period2_end,
            "stats": period2_stats
        },
        "comparison": {
            "total_incidents_change": total_change,
            "total_incidents_change_pct": round(total_change_pct, 2),
            "emergency_incidents_change": emergency_change,
            "emergency_incidents_change_pct": round(emergency_change_pct, 2)
        }
    }


@app.get("/analytics/incidents/engagement", tags=["analytics"])
async def get_engagement_metrics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    min_engagement_score: int = Query(0, ge=0, description="Minimum combined upvotes + comments")
):
    """
    Analyze incident engagement (upvotes, comments, likes)
    """
    base_filter = [incidents_table.c.iscityreport == False]
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    # Join incidents with engagement data
    query = select(
        incidents_table.c.id,
        incidents_table.c.name,
        incidents_table.c.upvotes,
        incidents_table.c.incidentcategoryid,
        incidents_table.c.datecreated,
        func.count(func.distinct(feedback_table.c.id)).label("comment_count"),
        func.count(func.distinct(likes_table.c.id)).label("like_count")
    ).select_from(
        incidents_table
        .outerjoin(feedback_table, incidents_table.c.id == feedback_table.c.postid)
        .outerjoin(likes_table, incidents_table.c.id == likes_table.c.postid)
    ).where(and_(*base_filter)).group_by(
        incidents_table.c.id,
        incidents_table.c.name,
        incidents_table.c.upvotes,
        incidents_table.c.incidentcategoryid,
        incidents_table.c.datecreated
    )
    
    results = await database.fetch_all(query)
    
    # Calculate engagement scores
    engaged_incidents = []
    
    for row in results:
        upvotes = int(row['upvotes'] or 0)
        comments = int(row['comment_count'])
        likes = int(row['like_count'])
        
        engagement_score = upvotes + comments + likes
        
        if engagement_score >= min_engagement_score:
            # Get category name
            cat_query = select(incidentcategories_table.c.name).where(
                incidentcategories_table.c.id == row['incidentcategoryid']
            )
            cat_result = await database.fetch_one(cat_query)
            
            engaged_incidents.append({
                "incident_id": row['id'],
                "incident_name": row['name'],
                "category": cat_result['name'] if cat_result else "Unknown",
                "upvotes": upvotes,
                "comments": comments,
                "likes": likes,
                "engagement_score": engagement_score,
                "created_date": row['datecreated'].isoformat() if row['datecreated'] else None
            })
    
    # Sort by engagement score
    engaged_incidents.sort(key=lambda x: x['engagement_score'], reverse=True)
    
    # Calculate summary stats
    total_upvotes = sum(inc['upvotes'] for inc in engaged_incidents)
    total_comments = sum(inc['comments'] for inc in engaged_incidents)
    total_likes = sum(inc['likes'] for inc in engaged_incidents)
    
    return {
        "summary": {
            "total_incidents": len(engaged_incidents),
            "total_upvotes": total_upvotes,
            "total_comments": total_comments,
            "total_likes": total_likes,
            "avg_engagement_score": round(sum(inc['engagement_score'] for inc in engaged_incidents) / len(engaged_incidents), 2) if engaged_incidents else 0
        },
        "top_engaged_incidents": engaged_incidents[:20]
    }


@app.get("/analytics/categories/performance", tags=["analytics"])
async def get_category_performance(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Analyze category performance: submission volume, resolution rate, avg resolution time
    """
    base_filter = [incidents_table.c.iscityreport == False]
    
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    j = incidents_table.join(
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )
    
    # Resolution time calculation
    resolution_time = func.extract(
        'epoch',
        incidents_table.c.dateupdated - incidents_table.c.datecreated
    ) / 3600  # Hours
    
    query = select(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name,
        func.count(incidents_table.c.id).label("total_incidents"),
        func.sum(case((incidents_table.c.status == "2", 1), else_=0)).label("resolved"),
        func.sum(case((incidents_table.c.status == "1", 1), else_=0)).label("published"),
        func.sum(case((incidents_table.c.status == "3", 1), else_=0)).label("rejected"),
        func.avg(
            case((incidents_table.c.status == "2", resolution_time), else_=None)
        ).label("avg_resolution_hours")
    ).select_from(j).where(and_(*base_filter)).group_by(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name
    ).order_by(func.count(incidents_table.c.id).desc())
    
    results = await database.fetch_all(query)
    
    performance_data = []
    
    for row in results:
        total = int(row['total_incidents'])
        resolved = int(row['resolved'] or 0)
        published = int(row['published'] or 0)
        rejected = int(row['rejected'] or 0)
        
        resolution_rate = (resolved / total * 100) if total > 0 else 0
        
        performance_data.append({
            "category_id": row['id'],
            "category_name": row['name'],
            "total_incidents": total,
            "resolved": resolved,
            "published": published,
            "rejected": rejected,
            "resolution_rate_pct": round(resolution_rate, 2),
            "avg_resolution_hours": round(float(row['avg_resolution_hours'] or 0), 2),
            "avg_resolution_days": round(float(row['avg_resolution_hours'] or 0) / 24, 2)
        })
    
    return {
        "categories": performance_data,
        "total_categories": len(performance_data)
    }


# ==================== DASHBOARD WIDGETS ====================

@app.get("/analytics/dashboard/widgets", tags=["analytics/dashboard"])
async def get_dashboard_widgets():
    """
    Get pre-configured widget data for dashboard display
    """
    now = datetime.now()
    today_start = datetime.combine(now.date(), datetime.min.time())
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Today's stats
    today_query = select(
        func.count(incidents_table.c.id).label("total"),
        func.sum(case((incidents_table.c.isemergency == True, 1), else_=0)).label("emergency")
    ).where(
        and_(
            incidents_table.c.datecreated >= today_start,
            incidents_table.c.iscityreport == False
        )
    )
    today_stats = await database.fetch_one(today_query)
    
    # This week's stats
    week_query = select(
        func.count(incidents_table.c.id)
    ).where(
        and_(
            incidents_table.c.datecreated >= week_start,
            incidents_table.c.iscityreport == False
        )
    )
    week_count = await database.fetch_one(week_query)
    
    # Pending approval count
    pending_query = select(
        func.count(incidents_table.c.id)
    ).where(
        and_(
            incidents_table.c.status == "0",
            incidents_table.c.iscityreport == False
        )
    )
    pending_count = await database.fetch_one(pending_query)
    
    # Active users this month
    active_users_query = select(
        func.count(func.distinct(incidents_table.c.createdby))
    ).where(
        and_(
            incidents_table.c.datecreated >= month_start,
            incidents_table.c.iscityreport == False
        )
    )
    active_users = await database.fetch_one(active_users_query)
    
    return {
        "today": {
            "total_incidents": int(today_stats['total']) if today_stats else 0,
            "emergency_incidents": int(today_stats['emergency'] or 0) if today_stats else 0
        },
        "this_week": {
            "total_incidents": int(week_count[0]) if week_count else 0
        },
        "pending_approval": int(pending_count[0]) if pending_count else 0,
        "active_users_this_month": int(active_users[0]) if active_users else 0,
        "timestamp": now.isoformat()
    }
