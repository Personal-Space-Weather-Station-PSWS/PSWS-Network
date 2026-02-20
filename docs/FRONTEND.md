# PSWS-Network Frontend Documentation

## Overview

The PSWS-Network frontend uses Django templates with Bootstrap 4, Mapbox GL JS for mapping, and Chart.js for data visualization.

## Technology Stack

- **CSS Framework**: Bootstrap 4
- **JavaScript Libraries**:
  - Mapbox GL JS v2.1.1 (interactive maps)
  - Chart.js (data visualization)
  - chartjs-plugin-zoom (interactive charts)
- **Template Engine**: Django Templates
- **Forms**: Django Crispy Forms with Bootstrap 4 theme

## Template Structure

```
src/apps/*/templates/
├── base.html                    # Base template (not used much)
├── base_stations.html          # Station pages base
├── base_observations.html      # Observation pages base
├── base_analysis.html          # Analysis pages base
└── {app_name}/                 # App-specific templates
```

## Key Pages

### Home Page (`home.html`)

**Features**:
- Interactive Mapbox map showing all stations
- Color-coded station markers by status:
  - Green: Online (< 24 hours)
  - Orange: Possibly Online (1-5 days)
  - Red: Offline (5-21 days)
  - Gray: Retired (> 21 days)
- Clickable markers with station details popups
- Navigation menu with user context

**Map Implementation**:
```javascript
mapboxgl.accessToken = '{{mapbox_access_token}}';
var map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/streets-v11',
    center: [-87.0, 33.0],
    zoom: 3.25
});

// Add markers for each station status
geojson_online.features.forEach(function(marker) {
    new mapboxgl.Marker({ color: "#008000", scale: .6 })
        .setLngLat(marker.geometry.coordinates)
        .setPopup(new mapboxgl.Popup({ offset: 25 })
            .setHTML('<h3><a href="' + marker.properties.URL + 
                     marker.properties.ID + '">' + 
                     marker.properties.title + '</a></h3>'))
        .addTo(map);
});
```

### Station List (`stations.html`)

**Features**:
- Paginated table of all registered stations
- django-tables2 integration
- Links to "My Stations" and "Add New Station"
- Station details accessible via clickable IDs

**Table Configuration**:
```python
class StationTable(tables.Table):
    class Meta:
        model = Station
        template_name = "django_tables2/bootstrap.html"
        fields = ("station_id", "user", "nickname", "grid", 
                  "elevation", "station_status")
```

### Observation List (`observation_list.html`)

**Features**:
- Filterable observation table
- Multiple filter options:
  - Station (dropdown)
  - Instrument type (multi-select)
  - Center frequency (multi-select)
  - Date range (start/end)
  - Geographic bounds (lat/lon)
- Pagination with quick jumps (±5 pages)
- Clickable observation names for details
- Plot indicator (green dot if plot exists)

**Filter Form**:
```django
<form action="" method="get" class="form-inline">
    {{ filter.form.as_p }}
    <input type="submit" value="Filter" />
    <a href="/observations/observation_list/">Clear Filters</a>
</form>
```

### Analysis Map (`analysis_map.html`)

**Features**:
- Date selector for finding active stations
- Interactive map with selectable stations
- Multi-station magnetometer plotting
- Chart.js with zoom/pan capabilities

**Station Selection**:
```javascript
// Toggle marker color on click
mapMarker.getElement().addEventListener('click', () => {
    isSelected = !isSelected;
    if (isSelected) {
        // Change to orange
        mapMarker.getElement()
            .querySelector('svg path').style.fill = '#FFA500';
        selectedStations.push(marker.properties.ID);
    } else {
        // Change back to green
        mapMarker.getElement()
            .querySelector('svg path').style.fill = '#008000';
        const index = selectedStations.indexOf(marker.properties.ID);
        if (index > -1) selectedStations.splice(index, 1);
    }
});
```

### Magnetometer Visualization (`display_graphs.html`)

**Features**:
- Multi-station 3-axis plots (Bx, By, Bz)
- 60-second windowed averaging
- Independent y-axis scaling
- Zoom and pan controls
- Time axis with UTC labels

**Chart Implementation**:
```javascript
var myChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: ts,
        datasets: [
            {
                label: "x",
                data: xs,
                borderColor: 'red',
                borderWidth: 0.3,
                pointRadius: 0.5,
            },
            // ... y and z datasets
        ]
    },
    options: {
        scales: {
            y: {
                min: -100,
                max: 100,
            }
        },
        plugins: {
            zoom: {
                pan: { enabled: true, mode: 'xy' },
                zoom: {
                    wheel: { enabled: true },
                    mode: 'xy',
                }
            }
        }
    }
});
```

## Navigation Menu

### Standard Menu Structure

```html
<ul class="Menu">
    <li><a href="/home">Home</a></li>
    <li><a href="/stations/stations">Stations</a></li>
    <li><a href="/observations/observation_list">Observations</a></li>
    <li><a href="/analysis/analysis">Analysis</a></li>
    <li><a href="/user_list">Users</a></li>
    <li>
        <form method="post" action="{% url 'logout' %}">
            {% csrf_token %}
            <button type="submit">Log Out</button>
        </form>
    </li>
    <li><a href="/signup/">Register your station</a></li>
    <li><a href="{% url 'profile' %}">{{ request.user.username }}</a></li>
    <li style="float:right"><a href="/about/">About</a></li>
</ul>
```

### Active Page Highlighting

Uses `class="active"` on current page menu item:
```html
<li><a class="active" href="/stations/stations">Stations</a></li>
```

## Forms

### Station Registration Form

**Fields**:
- Nickname (required)
- Maidenhead Grid Square (required, validated)
- Elevation (optional, meters above sea level)
- Antenna 1/2 (optional)
- Address fields (optional)
- Phone number (optional)

**Validation**:
```python
def clean(self):
    grid = self.cleaned_data.get('grid')
    try:
        latitude, longitude = mh.to_location(grid)
    except ValueError:
        raise ValidationError("Invalid Maidenhead grid square")
    return cleaned_data
```

### Observation Filter Form

**Custom Validation**:
```python
def clean(self):
    latitude = self.cleaned_data.get("latitude")
    longitude = self.cleaned_data.get("longitude")
    
    # Check both bounds provided
    if latitude.start is None and latitude.stop is not None:
        self._errors['latitude'].append(
            "Please enter values for both upper and lower bound."
        )
    
    # Check valid range (-90 to 90 for lat)
    if latitude.start < -90 or latitude.stop > 90:
        self._errors['latitude'].append(
            "Latitude must be between -90.0 and 90.0."
        )
```

## Static Files

### Structure
```
static/
├── PSWS/
│   └── media/
│       └── image001.png    # System architecture diagram
└── img/
    └── favicon.ico
```

### CSS Styling

**Menu Styling**:
```css
ul.Menu {
    list-style-type: none;
    background-color: #333;
}

li a {
    display: block;
    color: white;
    text-align: center;
    padding: 14px 16px;
    text-decoration: none;
}

li a:hover:not(.active) {
    background-color: #111;
}

.active {
    background-color: #04AA6D;
}
```

**Pagination Styling**:
```css
.pagination li:not(.active) {
    background-color: #333;
}
```

## Responsive Design

### Mobile Considerations

Filter forms use flexbox for responsiveness:
```css
.filter-form {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
}

@media (max-width: 768px) {
    .filter-form {
        flex-direction: column;
    }
}
```

## JavaScript Patterns

### CSRF Token Handling
```javascript
// In HTML head
<meta name="csrf-token" content="{{ csrf_token }}">

// In JavaScript
const csrftoken = document.querySelector('[name=csrf-token]').content;
```

### Form Submission Patterns

**Hidden Form Data**:
```javascript
document.getElementById('plotStationsForm')
    .addEventListener('submit', function(event) {
        const userDate = document.getElementById('start_datetime').value;
        document.getElementById('startDatetimeInput').value = userDate;
        document.getElementById('stationIdsInput').value = 
            JSON.stringify(selectedStations);
    });
```

## Crispy Forms Integration

### Configuration
```python
CRISPY_TEMPLATE_PACK = 'bootstrap4'
```

### Usage in Templates
```django
{% load crispy_forms_tags %}
<form method="post">
    {% csrf_token %}
    {{ form|crispy }}
    <button type="submit" class="btn btn-primary">Submit</button>
</form>
```

## django-tables2 Integration

### Table Definition
```python
class ObservationTable(tables.Table):
    fileName = tables.LinkColumn('select_download_range', 
                                 args=[A('id')])
    station = tables.LinkColumn('station_analysis', 
                                args=[A('station.id')])
    
    class Meta:
        model = Observation
        template_name = "django_tables2/bootstrap.html"
        fields = ("dataRate", "centerFrequency", "station", ...)
```

### Template Rendering
```django
{% load render_table from django_tables2 %}
{% render_table table %}
```

## Custom Template Tags/Filters

None currently implemented. Standard Django template tags used.

## Pagination

### Implementation
```django
<div class="pagination">
    <span class="step-links">
        {% if page_obj.has_previous %}
            <a href="?page=1">&laquo; first</a>
            <a href="?page={{ page_obj.previous_page_number }}">previous</a>
        {% endif %}
        
        <span class="current">
            Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}.
        </span>
        
        {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}">next</a>
            <a href="?page={{ page_obj.paginator.num_pages }}">last &raquo;</a>
        {% endif %}
    </span>
</div>
```

## UI/UX Improvements to Consider

1. **Add loading indicators** for long-running operations
2. **Implement AJAX filtering** for observation table
3. **Add real-time station status updates** via WebSockets
4. **Improve mobile responsiveness** of tables
5. **Add data export options** (CSV, JSON) to tables
6. **Implement dark mode** toggle
7. **Add keyboard shortcuts** for power users
8. **Improve error messaging** consistency

## Accessibility

### Current State
- Semantic HTML structure
- Form labels properly associated
- Color contrast generally adequate
- Keyboard navigation functional

### Improvements Needed
- Add ARIA labels to interactive elements
- Improve screen reader support for maps
- Add skip navigation links
- Ensure all interactive elements are keyboard accessible
- Add alt text to all images

## Performance Optimization

### Current Optimizations
- Static files served by Nginx
- Database query optimization with select_related
- Paginated results (8-10 items per page)

### Recommended Improvements
- Implement lazy loading for images
- Add client-side caching
- Minify CSS/JavaScript
- Use CDN for static assets
- Implement service workers for offline capability
