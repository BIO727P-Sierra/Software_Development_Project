def build_feedback(valid_records, rejected_records):

    feedback = {
        "success": True,
        "rows_parsed": len(valid_records),
        "rows_rejected": len(rejected_records),
        # Displaying the row/record number to help troubleshoot
        "rejection_details": [
            {
                "row_number": r["row_number"],
                "reason": r["reason"]
            }
            for r in rejected_records
        ]
    }

    return feedback

def error_feedback(error_message):

    return {
        "success": False,
        "error": str(error_message),
        "rows_parsed": 0,
        "rows_rejected": 0

    }
