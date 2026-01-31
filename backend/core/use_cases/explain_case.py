

from ..explanation.service import ExplanationService

def explain_issue(issue_type: str):
    service = ExplanationService()
    return service.generate({
        "issue_type": issue_type
    })

if __name__ == "__main__":
    # مثال عملي
    for issue in ["MISSING_DOCUMENT", "RULE_VIOLATION", "DATA_MISMATCH", "UNKNOWN"]:
        print(f"{issue}: ", explain_issue(issue))
