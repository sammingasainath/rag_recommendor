# Frontend Implementation Documentation

## Overview
This document outlines the implementation plan for the SHL Assessment Recommendation System's frontend using Streamlit. The frontend provides an intuitive interface for users to input their requirements and view recommended assessments along with evaluation metrics.

## Technology Stack
- **Framework**: Streamlit
- **Language**: Python 3.8+
- **Key Dependencies**:
  - streamlit
  - pandas
  - requests
  - plotly (for metrics visualization)

## UI Components

### 1. Sidebar Input Controls
- **Job Level Selection**
  - Component: `st.multiselect`
  - Options: Entry, Mid, Senior, Executive
  - Purpose: Filter assessments by job level

- **Test Type Selection**
  - Component: `st.multiselect`
  - Options: Cognitive, Personality, Technical Skill, Coding, Situational Judgement
  - Purpose: Filter assessments by test type

- **Duration Input**
  - Component: `st.number_input`
  - Range: 0-120 minutes
  - Purpose: Set maximum assessment duration

- **Submit Button**
  - Component: `st.button`
  - Action: Triggers API call to backend

### 2. Main Content Area

#### Results Table
- Component: `st.dataframe`
- Features:
  - Sortable columns
  - Built-in filtering
  - Interactive selection
- Columns:
  - Assessment Name
  - Description
  - Duration (minutes)
  - Job Level(s)
  - Test Type(s)
  - Relevance Score

#### Evaluation Metrics Section
- Components:
  - `st.metrics` for key numbers
  - `plotly` charts for visual representation
- Metrics Displayed:
  - Mean Recall@K
  - Mean Average Precision (MAP@K)
  - Performance trends (if available)

## Backend Integration

### API Endpoint Integration
```python
BASE_URL = "http://localhost:8000"
RECOMMEND_ENDPOINT = f"{BASE_URL}/recommend/"

# Request Format
payload = {
    "job_levels": List[str],
    "test_types": List[str],
    "max_duration": int
}

# Response Format
response = {
    "recommendations": List[dict],
    "metrics": {
        "recall_at_k": float,
        "map_at_k": float
    }
}
```

### Error Handling
- Network connectivity issues
- Invalid input validation
- Backend service unavailability
- Empty results handling

## User Experience Features

### 1. Loading States
- Spinner during API calls
- Progress bars for long operations
- Placeholder content while loading

### 2. Input Validation
- Duration range validation
- Required fields checking
- Input format verification

### 3. Responsive Design
- Adaptive layout for different screen sizes
- Collapsible sidebar for mobile views
- Scrollable results table

## File Structure
```
frontend/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Frontend dependencies
├── utils/
│   ├── api.py            # Backend API integration
│   ├── metrics.py        # Metrics visualization
│   └── formatting.py     # Data formatting utilities
└── assets/
    └── style.css         # Custom styling
```

## Implementation Steps

1. **Setup & Dependencies**
   - Create virtual environment
   - Install required packages
   - Setup development environment

2. **Core Implementation**
   - Create basic Streamlit app structure
   - Implement input controls
   - Add API integration
   - Create results display

3. **Enhanced Features**
   - Add sorting and filtering
   - Implement metrics visualization
   - Add error handling
   - Enhance UI/UX

4. **Testing & Optimization**
   - Test all user interactions
   - Verify API integration
   - Optimize performance
   - Cross-browser testing

## Future Enhancements

1. **Advanced Features**
   - Natural language input processing
   - Advanced filtering options
   - Batch processing capabilities
   - Export functionality

2. **UI Improvements**
   - Theme customization
   - Advanced visualizations
   - Mobile optimization
   - Accessibility improvements

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## Notes
- The UI is designed to be intuitive and user-friendly
- All components are modular for easy maintenance
- The design follows Streamlit best practices
- Error handling is implemented at all levels 