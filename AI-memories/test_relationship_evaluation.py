import json
from relationship_evaluations import evaluate_relationship

def main():
    """Test the relationship evaluation between ConsiglioDeiDieci and ShippingMogul"""
    
    # Sample data for testing
    evaluator_citizen = {
        "fields": {
            "Username": "ConsiglioDeiDieci",
            "FirstName": "Consiglio",
            "LastName": "Dei Dieci",
            "SocialClass": "Nobili"
        }
    }
    
    target_citizen = {
        "fields": {
            "Username": "ShippingMogul",
            "FirstName": "Isabella",
            "LastName": "Trevisan",
            "SocialClass": "Popolani"
        }
    }
    
    relationship = {
        "fields": {
            "TrustScore": 23.7,
            "StrengthScore": 0.0
        }
    }
    
    # Empty lists for relevancies as they weren't provided
    relevancies_evaluator_to_target = []
    relevancies_target_to_evaluator = []
    
    # Sample problems based on the system context
    problems_involving_both = [
        {"type": "zero_rent_business_leased"},
        {"type": "no_active_contracts"},
        {"type": "vacant_business"}
    ]
    
    # Evaluate the relationship
    result = evaluate_relationship(
        evaluator_citizen,
        target_citizen,
        relationship,
        relevancies_evaluator_to_target,
        relevancies_target_to_evaluator,
        problems_involving_both
    )
    
    # Print the result
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
