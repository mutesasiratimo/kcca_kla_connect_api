# KLA Konnect API - Analytics Implementation Guide

## Overview
This guide provides comprehensive analytics endpoints for the KLA Konnect incident reporting system.

## Code Review Findings

### Issues Identified
1. **Duplicate Code**: `/incidents` and `/reports` endpoints share nearly identical logic
2. **Missing Analytics**: No comprehensive reporting or insights endpoints
3. **Limited Aggregations**: Basic counting without deeper analysis
4. **No Export Functionality**: Cannot export data for external analysis

### Recommendations
1. Consolidate incident/report logic using query parameters
2. Add comprehensive analytics endpoints
3. Implement data export (CSV, JSON)
4. Add geospatial hotspot detection
5. Create dashboard widget endpoints

## New Analytics Endpoints

### 1. Incidents Overview
**Endpoint**: `GET /analytics/incidents/overview`

**Parameters**:
- `start_date` (optional): Filter start date (YYYY-MM-DD)
- `end_date` (optional): Filter end date (YYYY-MM-DD)
- `include_city_reports` (optional): Include city reports (default: false)

**Returns**:
- Status breakdown (archived, published, resolved, rejected)
- Emergency incident count
- Average resolution time
- Daily trend data

**Example Response**:
```json
{
  "status_breakdown": {
    "archived": 5,
    "published": 120,
    "resolved": 89,
    "rejected": 12,
    "total": 226
  },
  "emergency_incidents": 15,
  "avg_resolution_hours": 48.5,
  "daily_trend": [
    {"date": "2025-01-01", "count": 12},
    {"date": "2025-01-02", "count": 15}
  ]
}
```

### 2. Incidents by Category
**Endpoint**: `GET /analytics/incidents/by-category`

**Parameters**:
- `start_date`, `end_date`, `include_city_reports`
- `top_n`: Number of top categories (default: 10, max: 50)

**Returns**:
- Category breakdown with counts and percentages
- Status distribution per category
- Average upvotes per category

**Example Response**:
```json
{
  "categories": [
    {
      "category_id": "uuid",
      "category_name": "Potholes",
      "total_count": 85,
      "published": 60,
      "resolved": 20,
      "rejected": 5,
      "emergency": 3,
      "avg_upvotes": 4.2,
      "percentage": 37.6
    }
  ],
  "total_incidents": 226,
  "total_categories": 8
}
```

### 3. Geographic Hotspots (TOP 10)
**Endpoint**: `GET /analytics/incidents/hotspots`

**Parameters**:
- `radius_meters`: Clustering radius (default: 500, range: 100-5000)
- `min_incidents`: Minimum incidents for hotspot (default: 3, range: 2-20)
- `start_date`, `end_date`, `category_id`, `include_city_reports`
- `top_n`: Number of hotspots to return (default: 10, max: 50)

**Algorithm**:
1. Fetches all incidents with valid coordinates
2. Uses Haversine distance formula for geospatial calculations
3. Clusters incidents within specified radius
4. Filters clusters meeting minimum incident threshold
5. Calculates centroid for each hotspot
6. Returns top N hotspots by incident count

**Returns**:
- Geographic coordinates of hotspot centers
- Incident count per hotspot
- Status breakdown
- Most common category
- List of incident IDs in each hotspot

**Example Response**:
```json
{
  "hotspots": [
    {
      "center_lat": 0.347596,
      "center_long": 32.582520,
      "incident_count": 23,
      "location_name": "Kampala Road",
      "radius_meters": 500,
      "status_breakdown": {
        "1": 15,
        "2": 6,
        "3": 2
      },
      "top_category_id": "uuid",
      "top_category_name": "Potholes",
      "incident_ids": ["id1", "id2", "id3"]
    }
  ],
  "total_hotspots": 8,
  "parameters": {
    "radius_meters": 500,
    "min_incidents": 3,
    "top_n": 10
  }
}
```

### 4. User Activity Statistics
**Endpoint**: `GET /analytics/users/activity`

**Parameters**:
- `start_date`, `end_date`
- `user_type`: Filter by type (citizen, clerk, engineer, admin)

**Returns**:
- Total and active user counts
- Registration trends
- Top contributors (users with most incidents)

### 5. Time Series Analysis
**Endpoint**: `GET /analytics/incidents/time-series`

**Parameters**:
- `start_date`, `end_date`, `category_id`, `include_city_reports`
- `granularity`: day, week, month, year

**Returns**:
- Incident counts grouped by time period
- Status breakdown per period

### 6. Resolution Time Analysis
**Endpoint**: `GET /analytics/incidents/resolution-time`

**Parameters**:
- `start_date`, `end_date`, `category_id`

**Returns**:
- Average, min, max, median resolution times by category
- Number of resolved incidents per category

### 7. Geographic Distribution
**Endpoint**: `GET /analytics/geographic/distribution`

**Parameters**:
- `start_date`, `end_date`
- `grid_size_km`: Grid cell size (default: 1.0, range: 0.1-10.0)

**Returns**:
- Incident density by geographic grid cells
- Grid cell coordinates and incident counts

### 8. Period Comparison
**Endpoint**: `GET /analytics/incidents/comparison`

**Parameters**:
- `period1_start`, `period1_end`
- `period2_start`, `period2_end`

**Returns**:
- Side-by-side comparison of two time periods
- Percentage changes in key metrics

### 9. Engagement Metrics
**Endpoint**: `GET /analytics/incidents/engagement`

**Parameters**:
- `start_date`, `end_date`
- `min_engagement_score`: Filter threshold

**Returns**:
- Incidents ranked by engagement (upvotes + comments + likes)
- Engagement summary statistics

### 10. Category Performance
**Endpoint**: `GET /analytics/categories/performance`

**Parameters**:
- `start_date`, `end_date`

**Returns**:
- Per-category metrics: volume, resolution rate, avg resolution time

### 11. Export to CSV
**Endpoint**: `GET /analytics/export/incidents-csv`

**Parameters**:
- `start_date`, `end_date`, `status`, `category_id`, `include_city_reports`

**Returns**:
- CSV file download with incident data

### 12. Comprehensive Summary Report
**Endpoint**: `GET /analytics/reports/summary`

**Parameters**:
- `start_date`, `end_date`

**Returns**:
- Combined report with overview, categories, hotspots, and user activity

### 13. Dashboard Widgets
**Endpoint**: `GET /analytics/dashboard/widgets`

**Returns**:
- Pre-calculated stats for dashboard:
  - Today's incidents
  - This week's incidents
  - Pending approvals
  - Active users this month

## Implementation Steps

### Step 1: Add Analytics Endpoints to main.py

```python
# Copy the contents of analytics_endpoints.py into your main.py file
# Place them after your existing endpoints but before the server startup code
```

### Step 2: Test the Endpoints

```bash
# Test overview
curl "http://localhost:8000/analytics/incidents/overview?start_date=2025-01-01"

# Test hotspots
curl "http://localhost:8000/analytics/incidents/hotspots?radius_meters=500&min_incidents=3"

# Test category breakdown
curl "http://localhost:8000/analytics/incidents/by-category?top_n=10"
```

### Step 3: Add to API Documentation

The endpoints will automatically appear in your Swagger docs at:
- http://localhost:8000/docs

### Step 4: Frontend Integration

```javascript
// Example: Fetch hotspots
const fetchHotspots = async () => {
  const response = await fetch(
    '/analytics/incidents/hotspots?radius_meters=500&min_incidents=3&top_n=10'
  );
  const data = await response.json();
  
  // Display on map
  data.hotspots.forEach(hotspot => {
    addMarkerToMap(hotspot.center_lat, hotspot.center_long, {
      label: `${hotspot.incident_count} incidents`,
      color: getHotspotColor(hotspot.incident_count)
    });
  });
};

// Example: Export to CSV
const exportIncidents = () => {
  window.location.href = '/analytics/export/incidents-csv?start_date=2025-01-01';
};
```

## Performance Considerations

### Optimization Tips

1. **Database Indexing**:
```sql
-- Add indexes for better query performance
CREATE INDEX idx_incidents_datecreated ON incidents(datecreated);
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_category ON incidents(incidentcategoryid);
CREATE INDEX idx_incidents_location ON incidents(addresslat, addresslong);
CREATE INDEX idx_incidents_createdby ON incidents(createdby);
```

2. **Caching**:
- Cache frequently accessed analytics (dashboard widgets, top categories)
- Implement Redis or similar for 5-15 minute cache TTL
- Invalidate cache on new incident creation

3. **Pagination**:
- Use existing pagination for large datasets
- Limit default results to reasonable sizes

4. **Async Processing**:
- For very large datasets, consider background job processing
- Queue CSV exports for email delivery

## Security Considerations

1. **Authentication**: Most analytics endpoints should require authentication
   ```python
   @app.get("/analytics/...", dependencies=[Depends(jwtBearer())])
   ```

2. **Rate Limiting**: Already implemented in your middleware

3. **Data Privacy**: 
   - Don't expose sensitive user information in exports
   - Anonymize reporter details if needed

## Database Schema Suggestions

Consider adding these tables for better analytics:

```sql
-- Analytics cache table
CREATE TABLE analytics_cache (
    id UUID PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE,
    data JSONB,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Aggregate stats table (for faster dashboard queries)
CREATE TABLE daily_stats (
    id UUID PRIMARY KEY,
    stat_date DATE UNIQUE,
    total_incidents INTEGER,
    resolved_incidents INTEGER,
    emergency_incidents INTEGER,
    active_users INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Monitoring & Alerts

Set up monitoring for:
- Hotspot emergence (new areas with incident clusters)
- Resolution time SLA breaches
- Spike in emergency incidents
- Drop in user engagement

## Future Enhancements

1. **Predictive Analytics**:
   - Incident forecasting by category/location
   - Seasonal trend analysis

2. **Advanced Visualizations**:
   - Heat maps
   - Trend predictions
   - Network graphs (related incidents)

3. **Real-time Analytics**:
   - WebSocket-based live dashboard updates
   - Streaming incident data

4. **Machine Learning**:
   - Automatic incident categorization
   - Duplicate detection improvements
   - Priority scoring

## Support & Maintenance

- Review analytics queries monthly for performance
- Archive old incident data (>2 years) to separate tables
- Monitor slow queries and optimize
- Update geospatial algorithms as needed

## Conclusion

These analytics endpoints provide comprehensive insights into incident data, user behavior, and geographic patterns. They enable data-driven decision-making for city management and service delivery optimization.
