from pydantic import BaseModel, Field


class ExtractedPayload(BaseModel):
    patient: dict = Field(default_factory=dict)
    document: dict = Field(default_factory=dict)
    lab_results: list[dict] = Field(default_factory=list)
    imaging_findings: list[dict] = Field(default_factory=list)
    health_issues: list[dict] = Field(default_factory=list)
    doctor_summary_points: list[str] = Field(default_factory=list)
    followup_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
