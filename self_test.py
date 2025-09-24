import pandas as pd
import ast
import json
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib

class SmartAllocationEngine:
    def __init__(self):
        # Candidate and internship storage
        self.candidate_data: List[Dict[str, Any]] = []
        self.candidate_map: Dict[str, Dict[str, Any]] = {}  # email -> candidate
        self.internship_data: List[Dict[str, Any]] = []

        # TF-IDF for skill matching
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.skill_matrix = None

    # ---------------- Candidate Persistence ----------------
    def add_candidate(self, candidate_info: dict):
        email = candidate_info.get('email')
        if email in self.candidate_map:
            return self.candidate_map[email]['id']

        candidate_id = len(self.candidate_data) + 1
        candidate_info['id'] = candidate_id
        self.candidate_data.append(candidate_info)
        if email:
            self.candidate_map[email] = candidate_info
        return candidate_id

    def get_candidate_by_email(self, email: str):
        return self.candidate_map.get(email)

    def save_candidates(self, filepath='candidates.json'):
        with open(filepath, 'w') as f:
            json.dump(self.candidate_data, f, indent=2)

    def load_candidates(self, filepath='candidates.json'):
        try:
            with open(filepath, 'r') as f:
                self.candidate_data = json.load(f)
                self.candidate_map = {c['email']: c for c in self.candidate_data if 'email' in c}
        except FileNotFoundError:
            self.candidate_data = []
            self.candidate_map = {}
            
    # Add this inside SmartAllocationEngine class
    def make_json_serializable(self, obj):
        """
    Recursively convert sets to lists so that the object can be JSON-serialized.
    """
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self.make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.make_json_serializable(i) for i in obj]
        else:
            return obj


    # ---------------- Internship Data ----------------
    def load_internship_data_from_csv(self, filepath: str):
        df = pd.read_csv(r"D:\sih\internships_dummy_dataset.csv")
        self.internship_data = []
        skill_texts = []

        for _, row in df.iterrows():
            skills = ast.literal_eval(row['skills_required']) if isinstance(row['skills_required'], str) else []
            internship = {
                'id': int(row['id']),
                'title': row['title'],
                'company': row['company'],
                'sector': row['sector'].lower(),
                'location': row['location'].lower(),
                'skills_required': skills,
                'skills_set': set(skill.lower() for skill in skills),
                'education_level': row['education_level'],
                'capacity': int(row['capacity']),
                'duration_months': int(row['duration_months']),
                'stipend': int(row['stipend']),
                'rural_friendly': bool(row['rural_friendly']),
                'diversity_focused': bool(row['diversity_focused'])
            }
            self.internship_data.append(internship)
            skill_texts.append(' '.join(skills).lower())

        # Build TF-IDF matrix for all internships
        if skill_texts:
            self.skill_matrix = self.vectorizer.fit_transform(skill_texts)

    # ---------------- Matching Scores ----------------
    def calculate_skill_match_score(self, candidate_skills, internship):
        if not candidate_skills or not internship['skills_required']:
            return 0.0
        candidate_text = ' '.join(candidate_skills).lower()
        internship_index = internship['id'] - 1  # assuming IDs start at 1
        internship_vector = self.skill_matrix[internship_index]
        candidate_vector = self.vectorizer.transform([candidate_text])
        score = cosine_similarity(candidate_vector, internship_vector)[0][0]
        return float(score)

    def calculate_location_preference_score(self, candidate_location, internship_location,
                                           candidate_prefers_rural, internship_rural_friendly):
        if candidate_location.lower() == internship_location.lower():
            return 1.0
        if candidate_prefers_rural and internship_rural_friendly:
            return 0.8
        return 0.6

    def calculate_education_match_score(self, candidate_education, internship_education):
        levels = {'Diploma': 1, 'Bachelor': 2, 'Master': 3, 'PhD': 4}
        c = levels.get(candidate_education, 2)
        i = levels.get(internship_education, 2)
        if c == i: return 1.0
        if c > i: return 0.8
        return 0.4

    def calculate_sector_interest_score(self, candidate_interests, internship_sector):
        if not candidate_interests: return 0.5
        return 1.0 if internship_sector.lower() in [s.lower() for s in candidate_interests] else 0.3

    def calculate_diversity_score(self, candidate_info, internship_info):
        score = 0.0
        if internship_info.get('diversity_focused', False):
            score += 0.3
        if candidate_info.get('from_rural_area', False):
            score += 0.2
        if candidate_info.get('social_category') in ['SC', 'ST', 'OBC']:
            score += 0.2
        if candidate_info.get('first_generation_graduate', False):
            score += 0.1
        return min(score, 1.0)

    # ---------------- Recommendations ----------------
    def get_recommendations(self, candidate_info, top_n=5):
        recommendations = []

        for internship in self.internship_data:
            skill_score = self.calculate_skill_match_score(candidate_info.get('skills', []), internship)
            location_score = self.calculate_location_preference_score(
                candidate_info.get('location', ''),
                internship['location'],
                candidate_info.get('prefers_rural', False),
                internship['rural_friendly']
            )
            education_score = self.calculate_education_match_score(
                candidate_info.get('education_level', 'Bachelor'),
                internship['education_level']
            )
            sector_score = self.calculate_sector_interest_score(
                candidate_info.get('sector_interests', []),
                internship['sector']
            )
            diversity_score = self.calculate_diversity_score(candidate_info, internship)

            weights = {'skill': 0.3, 'location': 0.2, 'education': 0.2, 'sector': 0.15, 'diversity': 0.15}
            overall_score = (
                skill_score * weights['skill'] +
                location_score * weights['location'] +
                education_score * weights['education'] +
                sector_score * weights['sector'] +
                diversity_score * weights['diversity']
            )

            recommendations.append({
                'internship': internship,
                'scores': {
                    'overall': round(overall_score, 3),
                    'skill_match': round(skill_score, 3),
                    'location_match': round(location_score, 3),
                    'education_match': round(education_score, 3),
                    'sector_match': round(sector_score, 3),
                    'diversity_bonus': round(diversity_score, 3)
                },
                'match_reasons': self._generate_match_reasons(skill_score, location_score, education_score, sector_score, diversity_score)
            })

        recommendations.sort(key=lambda x: x['scores']['overall'], reverse=True)
    
    # Convert all sets in recommendations to lists before returning
        return self.make_json_serializable(recommendations[:top_n])


    def _generate_match_reasons(self, skill_score, location_score, education_score, sector_score, diversity_score):
        reasons = []
        if skill_score > 0.7: reasons.append("Strong skill alignment")
        elif skill_score > 0.4: reasons.append("Good skill match")
        if location_score > 0.8: reasons.append("Perfect location match")
        elif location_score > 0.6: reasons.append("Good location fit")
        if education_score > 0.8: reasons.append("Education level matches")
        if sector_score > 0.8: reasons.append("Matches your sector interests")
        if diversity_score > 0.3: reasons.append("Supports diversity and inclusion")
        return reasons

    # ---------------- Model Persistence ----------------
    def save_model(self, filepath):
        joblib.dump({
            'candidate_data': self.candidate_data,
            'internship_data': self.internship_data
        }, filepath)

    def load_model(self, filepath):
        data = joblib.load(filepath)
        self.candidate_data = data['candidate_data']
        self.internship_data = data['internship_data']
