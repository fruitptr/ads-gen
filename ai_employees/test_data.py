import uuid

# Sample test data for AI employee tasks
test_task_data = [
    {
        "user_id": uuid.uuid4(),
        "data": {
            "marcus": {
                "adsPerDay": "20",
                "adGuidance": "",
                "days": ["Mon", "Wed", "Fri"]
            },
            "valentina": {
                "custom": "ensure my brand logo is there",
                "spell": True,
                "grammar": True,
                "visuals": True,
                "claims": True,
                "copyright": True,
                "policy": True,
                "offensive": True,
                "layout": True,
                "faces": True,
                "cta": True,
                "multiLang": True,
                "prompt": True,
                "overpromise": True
            }
        }
    },
    {
        "user_id": uuid.uuid4(),
        "data": {
            "marcus": {
                "adsPerDay": "10",
                "adGuidance": "Make sure the background is dark and the text is white",
                "days": ["Mon", "Wed", "Fri", "Sat"]
            }
        }
    }
]