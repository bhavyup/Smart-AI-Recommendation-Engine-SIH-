from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
from smart_allocation_engine import SmartAllocationEngine
from language_support import LanguageSupport

app = Flask(__name__)
CORS(app)

# Initialize the AI engine and language support
ai_engine = SmartAllocationEngine()
ai_engine.load_sample_data()
language_support = LanguageSupport()

@app.route('/')
def landing():
    """Landing page with navigation options"""
    return render_template('landing.html')

@app.route('/candidate')
def index():
    """Main page with candidate input form"""
    return render_template('index.html')

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard for system management"""
    return render_template('admin_dashboard.html')

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    """API endpoint to get internship recommendations"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'education_level', 'skills', 'location', 'sector_interests']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Process candidate data
        candidate_info = {
            'name': data['name'],
            'education_level': data['education_level'],
            'skills': data['skills'] if isinstance(data['skills'], list) else [data['skills']],
            'location': data['location'],
            'sector_interests': data['sector_interests'] if isinstance(data['sector_interests'], list) else [data['sector_interests']],
            'prefers_rural': data.get('prefers_rural', False),
            'from_rural_area': data.get('from_rural_area', False),
            'social_category': data.get('social_category', ''),
            'first_generation_graduate': data.get('first_generation_graduate', False)
        }
        
        # Get recommendations
        recommendations = ai_engine.get_recommendations(candidate_info, top_n=5)
        
        # Add candidate to system
        candidate_id = ai_engine.add_candidate(candidate_info)
        
        return jsonify({
            'success': True,
            'candidate_id': candidate_id,
            'recommendations': recommendations
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/internships')
def get_internships():
    """Get all available internships"""
    return jsonify({
        'success': True,
        'internships': ai_engine.internship_data
    })

@app.route('/api/candidates')
def get_candidates():
    """Get all registered candidates"""
    return jsonify({
        'success': True,
        'candidates': ai_engine.candidate_data
    })

@app.route('/api/languages')
def get_languages():
    """Get supported languages"""
    return jsonify({
        'success': True,
        'languages': language_support.get_supported_languages()
    })

@app.route('/api/translations/<language_code>')
def get_translations(language_code):
    """Get translations for a specific language"""
    language_support.set_language(language_code)
    return jsonify({
        'success': True,
        'translations': language_support.get_all_texts()
    })

@app.route('/api/analytics')
def get_analytics():
    """Get analytics data for dashboard"""
    try:
        # Calculate analytics data
        total_candidates = len(ai_engine.candidate_data)
        total_internships = len(ai_engine.internship_data)
        
        # Calculate diversity metrics
        diversity_candidates = sum(1 for c in ai_engine.candidate_data 
                                 if c.get('from_rural_area') or 
                                    c.get('social_category') in ['SC', 'ST', 'OBC'] or
                                    c.get('first_generation_graduate'))
        
        diversity_rate = (diversity_candidates / total_candidates * 100) if total_candidates > 0 else 0
        
        # Calculate sector distribution
        sector_counts = {}
        for internship in ai_engine.internship_data:
            sector = internship['sector']
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        # Calculate location distribution
        location_counts = {}
        for candidate in ai_engine.candidate_data:
            location = candidate['location']
            location_counts[location] = location_counts.get(location, 0) + 1
        
        # Calculate education distribution
        education_counts = {}
        for candidate in ai_engine.candidate_data:
            education = candidate['education_level']
            education_counts[education] = education_counts.get(education, 0) + 1
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_candidates': total_candidates,
                'total_internships': total_internships,
                'diversity_rate': round(diversity_rate, 1),
                'sector_distribution': sector_counts,
                'location_distribution': location_counts,
                'education_distribution': education_counts
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/candidates', methods=['POST'])
def add_candidate():
    """Add a new candidate"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'education_level', 'skills', 'location', 'sector_interests']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Process candidate data
        candidate_info = {
            'name': data['name'],
            'education_level': data['education_level'],
            'skills': data['skills'] if isinstance(data['skills'], list) else [data['skills']],
            'location': data['location'],
            'sector_interests': data['sector_interests'] if isinstance(data['sector_interests'], list) else [data['sector_interests']],
            'prefers_rural': data.get('prefers_rural', False),
            'from_rural_area': data.get('from_rural_area', False),
            'social_category': data.get('social_category', ''),
            'first_generation_graduate': data.get('first_generation_graduate', False)
        }
        
        # Add candidate to system
        candidate_id = ai_engine.add_candidate(candidate_info)
        
        return jsonify({
            'success': True,
            'candidate_id': candidate_id,
            'message': 'Candidate added successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
