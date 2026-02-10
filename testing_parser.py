from parse_data import parse_data
from qc import validate_data
from feedback import build_feedback
from feedback import error_feedback

file_path = # To be uploaded in flask

def test(file_path):
    try:
        parsed = parse_data(file_path)
        valid, rejected = validate_data(parsed)
        feedback = build_feedback(valid, rejected)

        print(feedback)
    except Exception as e:
        feedback = error_feedback(e)
        print("UPLOAD FAILED")
        print(feedback)

if __name__ == "__main__":
    test(file_path)