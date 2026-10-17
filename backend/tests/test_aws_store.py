import pytest
import os
import json
from backend.app.aws_store import AWSManager

def test_aws_manager_initialization(tmp_path):
    mgr = AWSManager(local_fallback_dir=str(tmp_path))
    assert mgr.bucket == "swarmtwin-evidence-frames"
    assert mgr.table_name == "SwarmTwinIncidents"

def test_aws_manager_upload_frame(tmp_path):
    mgr = AWSManager(local_fallback_dir=str(tmp_path))
    dummy_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" # JPEG header
    filename = "test_incident_primary.jpg"
    
    url = mgr.upload_frame(dummy_bytes, filename)
    assert "https://swarmtwin-evidence-frames.s3.amazonaws.com/test_incident_primary.jpg" in url
    
    # Check that local fallback frame was saved
    local_file = os.path.join(str(tmp_path), filename)
    assert os.path.exists(local_file)
    with open(local_file, "rb") as f:
        assert f.read() == dummy_bytes

def test_aws_manager_save_incident(tmp_path):
    mgr = AWSManager(local_fallback_dir=str(tmp_path))
    incident_id = "INC-AWS-TEST-001"
    final_status = "ESCALATE_HUMAN_REVIEW"
    trace = [
        {"step": 1, "phase": "INITIAL_PERCEPTION", "confidence": 0.5},
        {"step": 2, "phase": "VERIFICATION_AFTER_ACTION", "confidence": 0.9}
    ]
    
    item = mgr.save_incident(incident_id, final_status, trace)
    assert item["IncidentId"] == incident_id
    assert item["FinalStatus"] == final_status
    assert "TraceLog" in item
    
    # Check local fallback JSON record
    local_record = os.path.join(str(tmp_path), f"{incident_id}.json")
    assert os.path.exists(local_record)
    with open(local_record, "r") as f:
        data = json.load(f)
        assert data["IncidentId"] == incident_id
        assert data["FinalStatus"] == final_status
