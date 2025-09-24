#!/usr/bin/env python3
"""
Demo script for AI Smart Allocation Engine
Tests the system with sample candidate data
"""

from smart_allocation_engine import SmartAllocationEngine
import json

def main():
    print("🚀 AI Smart Allocation Engine - Demo")
    print("=" * 50)
    
    # Initialize the engine
    engine = SmartAllocationEngine()
    engine.load_sample_data()
    
    # Sample candidates for testing
    test_candidates = [
        {
            'name': 'Priya Sharma',
            'education_level': 'Bachelor',
            'skills': ['Python', 'JavaScript', 'React', 'SQL'],
            'location': 'Bangalore',
            'sector_interests': ['Technology', 'Software Development'],
            'prefers_rural': False,
            'from_rural_area': False,
            'social_category': 'General',
            'first_generation_graduate': False
        },
        {
            'name': 'Raj Kumar',
            'education_level': 'Master',
            'skills': ['Python', 'Machine Learning', 'Statistics', 'Data Analysis'],
            'location': 'Mumbai',
            'sector_interests': ['Technology', 'Data Science'],
            'prefers_rural': False,
            'from_rural_area': True,
            'social_category': 'OBC',
            'first_generation_graduate': True
        },
        {
            'name': 'Sunita Devi',
            'education_level': 'Bachelor',
            'skills': ['Digital Marketing', 'Social Media', 'Content Writing'],
            'location': 'Delhi',
            'sector_interests': ['Marketing', 'Communication'],
            'prefers_rural': True,
            'from_rural_area': True,
            'social_category': 'SC',
            'first_generation_graduate': True
        }
    ]
    
    print(f"📊 Loaded {len(engine.internship_data)} internships")
    print(f"👥 Testing with {len(test_candidates)} sample candidates\n")
    
    # Test each candidate
    for i, candidate in enumerate(test_candidates, 1):
        print(f"🧪 Test Case {i}: {candidate['name']}")
        print("-" * 30)
        
        # Get recommendations
        recommendations = engine.get_recommendations(candidate, top_n=3)
        
        print(f"📋 Profile: {candidate['education_level']} in {', '.join(candidate['sector_interests'])}")
        print(f"📍 Location: {candidate['location']}")
        print(f"🛠️ Skills: {', '.join(candidate['skills'])}")
        
        if candidate['from_rural_area']:
            print("🌾 From rural area")
        if candidate['social_category'] != 'General':
            print(f"👥 Social category: {candidate['social_category']}")
        if candidate['first_generation_graduate']:
            print("🎓 First generation graduate")
        
        print(f"\n🎯 Top {len(recommendations)} Recommendations:")
        
        for j, rec in enumerate(recommendations, 1):
            internship = rec['internship']
            scores = rec['scores']
            reasons = rec['match_reasons']
            
            print(f"\n  {j}. {internship['title']} at {internship['company']}")
            print(f"     📍 {internship['location']} | 💰 ₹{internship['stipend']:,}/month")
            print(f"     🎯 Match Score: {scores['overall']:.1%}")
            print(f"     📊 Breakdown: Skills({scores['skill_match']:.1%}) | Location({scores['location_match']:.1%}) | Education({scores['education_match']:.1%})")
            print(f"     ✅ Reasons: {', '.join(reasons)}")
            
            if internship['rural_friendly']:
                print(f"     🌾 Rural-friendly opportunity")
            if internship['diversity_focused']:
                print(f"     👥 Diversity-focused program")
        
        print("\n" + "="*50 + "\n")
    
    # Add candidates to the system
    print("💾 Adding candidates to the system...")
    for candidate in test_candidates:
        candidate_id = engine.add_candidate(candidate)
        print(f"✅ Added {candidate['name']} with ID: {candidate_id}")
    
    print(f"\n📈 System Statistics:")
    print(f"   • Total candidates: {len(engine.candidate_data)}")
    print(f"   • Total internships: {len(engine.internship_data)}")
    
    # Test API-like functionality
    print(f"\n🔧 Testing API functionality...")
    
    # Test skill matching
    test_skills = ['Python', 'JavaScript']
    internship_skills = ['Python', 'JavaScript', 'React', 'SQL']
    skill_score = engine.calculate_skill_match_score(test_skills, internship_skills)
    print(f"   • Skill matching test: {skill_score:.1%} match")
    
    # Test diversity scoring
    test_candidate = test_candidates[1]  # Raj Kumar
    test_internship = engine.internship_data[0]
    diversity_score = engine.calculate_diversity_score(test_candidate, test_internship)
    print(f"   • Diversity scoring test: {diversity_score:.1%} bonus")
    
    print(f"\n🎉 Demo completed successfully!")
    print(f"🌐 To run the web application: python app.py")
    print(f"📱 Then visit: http://localhost:5000")

if __name__ == "__main__":
    main()


