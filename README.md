# AI Smart Allocation Engine for PM Internship Scheme

A comprehensive AI-powered system that intelligently matches candidates with internship opportunities based on skills, qualifications, location preferences, and sector interests, while incorporating affirmative action considerations.

## 🎯 Problem Statement

The system addresses the need for an automated, intelligent platform that can:
- Match candidates with suitable internship opportunities
- Consider skills, qualifications, and location preferences
- Account for affirmative action and diversity requirements
- Support rural/aspirational district representation
- Optimize internship capacity allocation

## ✨ Features

### Core Functionality
- **AI-Powered Matching**: Uses ML algorithms to score and rank internship matches
- **Multi-Factor Scoring**: Considers skills, location, education, sector interests, and diversity
- **Affirmative Action Support**: Includes rural area, social category, and first-generation graduate considerations
- **Real-time Recommendations**: Provides instant, personalized internship suggestions

### User Experience
- **Mobile-Responsive Design**: Optimized for mobile devices and tablets
- **Intuitive UI**: Clean, modern interface with visual cards and minimal text
- **Visual Feedback**: Clear match scores, reasons, and progress indicators
- **Accessibility**: Designed for users across different technical backgrounds

### Technical Features
- **RESTful API**: Clean API endpoints for integration
- **Scalable Architecture**: Modular design for easy expansion
- **Data Persistence**: Candidate and internship data management
- **Extensible Framework**: Ready for regional language support

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone or download the project**
   ```bash
   # If you have git
   git clone <repository-url>
   cd sih-project
   
   # Or simply download and extract the files
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the demo**
   ```bash
   python demo.py
   ```

4. **Start the web application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open your browser
   - Navigate to `http://localhost:5000`
   - Start exploring internship matches!

## 📱 Usage Guide

### For Candidates

1. **Fill out the form** with your information:
   - Personal details (name, education level)
   - Skills (comma-separated list)
   - Location preferences
   - Sector interests
   - Background information for diversity considerations

2. **Submit the form** to get AI-powered recommendations

3. **Review matches** with detailed scoring and explanations

4. **Apply to internships** that interest you

### For Administrators

- **API Endpoints**:
  - `GET /api/internships` - View all available internships
  - `GET /api/candidates` - View registered candidates
  - `POST /api/recommendations` - Get recommendations for a candidate

## 🧠 AI Algorithm Details

### Matching Algorithm

The system uses a weighted scoring approach with the following components:

1. **Skill Matching (30% weight)**
   - Compares candidate skills with internship requirements
   - Uses fuzzy matching for skill variations
   - Considers skill relevance and depth

2. **Location Preference (20% weight)**
   - Exact location matches get highest score
   - Rural-friendly internships get bonus for rural candidates
   - Regional proximity considerations

3. **Education Level (20% weight)**
   - Exact education level matches preferred
   - Higher education candidates can apply to lower-level positions
   - Structured education hierarchy

4. **Sector Interest (15% weight)**
   - Matches candidate interests with internship sectors
   - Multiple interest support
   - Cross-sector compatibility

5. **Diversity & Affirmative Action (15% weight)**
   - Rural area origin bonus
   - Social category considerations (SC/ST/OBC)
   - First-generation graduate support
   - Diversity-focused internship preferences

### Scoring Formula
```
Overall Score = (Skill × 0.3) + (Location × 0.2) + (Education × 0.2) + (Sector × 0.15) + (Diversity × 0.15)
```

## 🏗️ Architecture

### Backend Components

- **`smart_allocation_engine.py`**: Core AI engine with matching algorithms
- **`app.py`**: Flask web application with API endpoints
- **`demo.py`**: Demonstration script with test cases

### Frontend Components

- **`templates/index.html`**: Main user interface
- **Bootstrap 5**: Responsive CSS framework
- **Font Awesome**: Icons and visual elements
- **Custom CSS**: Modern styling and animations

### Data Models

#### Candidate Model
```python
{
    'name': str,
    'education_level': str,  # Diploma, Bachelor, Master, PhD
    'skills': List[str],
    'location': str,
    'sector_interests': List[str],
    'prefers_rural': bool,
    'from_rural_area': bool,
    'social_category': str,  # General, SC, ST, OBC
    'first_generation_graduate': bool
}
```

#### Internship Model
```python
{
    'id': int,
    'title': str,
    'company': str,
    'sector': str,
    'location': str,
    'skills_required': List[str],
    'education_level': str,
    'capacity': int,
    'duration_months': int,
    'stipend': int,
    'rural_friendly': bool,
    'diversity_focused': bool
}
```

## 🔧 API Documentation

### Endpoints

#### `POST /api/recommendations`
Get internship recommendations for a candidate.

**Request Body:**
```json
{
    "name": "John Doe",
    "education_level": "Bachelor",
    "skills": ["Python", "JavaScript"],
    "location": "Bangalore",
    "sector_interests": ["Technology"],
    "social_category": "General",
    "prefers_rural": false,
    "from_rural_area": false,
    "first_generation_graduate": false
}
```

**Response:**
```json
{
    "success": true,
    "candidate_id": 1,
    "recommendations": [
        {
            "internship": { /* internship object */ },
            "scores": {
                "overall": 0.85,
                "skill_match": 0.75,
                "location_match": 1.0,
                "education_match": 1.0,
                "sector_match": 1.0,
                "diversity_bonus": 0.0
            },
            "match_reasons": ["Strong skill alignment", "Perfect location match"]
        }
    ]
}
```

#### `GET /api/internships`
Get all available internships.

#### `GET /api/candidates`
Get all registered candidates.

## 🌐 Regional Language Support

The system is designed with internationalization in mind:

- **Language Framework**: Ready for i18n implementation
- **Unicode Support**: Full UTF-8 character support
- **Localization Ready**: Structured for easy translation
- **Cultural Considerations**: Respects regional preferences

### Adding New Languages

1. Create language files in `translations/` directory
2. Update the frontend to use translation keys
3. Modify the backend to serve localized content

## 📊 Sample Data

The system includes comprehensive sample data:

- **5 Internship Opportunities** across different sectors
- **3 Test Candidates** with diverse backgrounds
- **Multiple Skill Sets** covering technology, marketing, finance, and healthcare
- **Geographic Diversity** across major Indian cities
- **Diversity Considerations** including rural and social category representation

## 🧪 Testing

### Running Tests

```bash
# Run the demo script
python demo.py

# Test specific components
python -c "from smart_allocation_engine import SmartAllocationEngine; engine = SmartAllocationEngine(); print('✅ Engine loaded successfully')"
```

### Test Cases

The demo includes three comprehensive test cases:

1. **Tech-focused candidate** (Priya Sharma)
2. **Data science candidate with rural background** (Raj Kumar)
3. **Marketing candidate with diversity considerations** (Sunita Devi)

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Using Docker (if Dockerfile is created)
docker build -t internship-engine .
docker run -p 5000:5000 internship-engine
```

## 🔮 Future Enhancements

### Planned Features
- **Machine Learning Integration**: Advanced ML models for better matching
- **Real-time Chat**: Candidate-employer communication
- **Analytics Dashboard**: Admin insights and reporting
- **Mobile App**: Native mobile application
- **Blockchain Integration**: Secure credential verification
- **Video Interviews**: Integrated interview scheduling

### Scalability Considerations
- **Database Integration**: PostgreSQL/MongoDB for production
- **Caching Layer**: Redis for performance optimization
- **Load Balancing**: Multiple server instances
- **Microservices**: Service-oriented architecture
- **Cloud Deployment**: AWS/Azure/GCP integration

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Code Standards
- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions
- Include type hints where appropriate

## 📄 License

This project is developed for the Smart India Hackathon 2024 under the Ministry of Corporate Affairs.

## 👥 Team

- **AI Developer**: [Your Name]
- **Problem Statement**: AI-Based Smart Allocation Engine for PM Internship Scheme
- **Organization**: Ministry of Corporate Affairs

## 📞 Support

For questions, issues, or contributions:
- Create an issue in the repository
- Contact the development team
- Check the documentation for common solutions

---

**Built with ❤️ for Smart India Hackathon 2024**


