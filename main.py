import os
import resend
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]
RESEND_API_KEY: str = os.environ["RESEND_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
resend.api_key = RESEND_API_KEY


class InquiryRequest(BaseModel):
    name: str
    email: EmailStr
    company: str | None = None
    subject: str
    message: str


@app.get("/")
def health():
    return {"status": "ok", "service": "tavaone-inquiries-api"}


@app.post("/inquiry")
async def submit_inquiry(inquiry: InquiryRequest):
    # 1. Save to Supabase
    try:
        supabase.table("inquiries").insert({
            "name": inquiry.name,
            "email": inquiry.email,
            "company": inquiry.company,
            "subject": inquiry.subject,
            "message": inquiry.message,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # 2. Send email notification via Resend
    try:
        resend.Emails.send({
            "from": "inquiries@tavaone.com",
            "to": "support@tavaone.com",
            "reply_to": inquiry.email,
            "subject": f"[Dev Inquiry] {inquiry.subject}",
            "html": f"""
                <h2>New Developer Inquiry</h2>
                <table style="font-family: sans-serif; font-size: 14px; border-collapse: collapse;">
                    <tr><td style="padding: 6px 12px; font-weight: bold;">Name</td>
                        <td style="padding: 6px 12px;">{inquiry.name}</td></tr>
                    <tr><td style="padding: 6px 12px; font-weight: bold;">Email</td>
                        <td style="padding: 6px 12px;"><a href="mailto:{inquiry.email}">{inquiry.email}</a></td></tr>
                    <tr><td style="padding: 6px 12px; font-weight: bold;">Company</td>
                        <td style="padding: 6px 12px;">{inquiry.company or "—"}</td></tr>
                    <tr><td style="padding: 6px 12px; font-weight: bold;">Subject</td>
                        <td style="padding: 6px 12px;">{inquiry.subject}</td></tr>
                    <tr><td style="padding: 6px 12px; font-weight: bold;">Message</td>
                        <td style="padding: 6px 12px; white-space: pre-wrap;">{inquiry.message}</td></tr>
                </table>
            """,
        })
    except Exception as e:
        # Inquiry is saved — don't fail the whole request over email
        print(f"Resend error (non-fatal): {str(e)}")

    return {"success": True, "message": "Inquiry received. We'll be in touch soon."}
