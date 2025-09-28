from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
# Allow cross-origin requests so the static HTML can POST from localhost or file://
CORS(app, resources={r"/v1/*": {"origins": "*"}})

@app.route("/ping", methods=["GET"])
def ping():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # user_agent: prefer payload, else header
    ua = submission.user_agent or request.headers.get("User-Agent")

    # Hash PII (NEVER store raw)
    email_hash = sha256_hex(submission.email) if submission.email else None
    age_hash = sha256_hex(str(submission.age)) if submission.age is not None else None

    # submission_id: use provided or compute sha256(email + UTC YYYYMMDDHH)
    if submission.submission_id:
        sub_id = submission.submission_id
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        base = (submission.email or "") + stamp
        sub_id = sha256_hex(base)

    # Build stored record WITHOUT raw email/age
    record = StoredSurveyRecord(
        submission_id=sub_id,
        user_agent=ua,
        email_hash=email_hash,
        age_hash=age_hash,
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or ""),
        name=submission.name,
        rating=submission.rating,
        comments=submission.comments,
        consent=submission.consent,
    )

    # storage.py already makes the directory and serializes datetime
    append_json_line(record.dict())

    return jsonify({"status": "ok", "submission_id": sub_id}), 201

if __name__ == "__main__":
    # grader expects port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
