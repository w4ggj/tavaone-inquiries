from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
import resend
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tavaone.com"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
resend.api_key = os.environ["RESEND_API_KEY"]

class Inquiry(BaseModel):
    name: str
    email: str
    project_type: str | None = None
    message: str

@app.post("/inquiry")
async def submit_inquiry(data: Inquiry):
    try:
        # Save to Supabase
        sb.table("inquiries").insert({
            "name": data.name,
            "email": data.email,
            "project_type": data.project_type,
            "message": data.message,
            "status": "new"
        }).execute()

        # Send notification email
        resend.Emails.send({
            "from": "TavaOne Inquiries <inquiries@tavaone.com>",
            "to": "support@tavaone.com",
            "subject": f"New Inquiry — {data.project_type or 'General'} from {data.name}",
            "html": f"""
                <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0f172a;color:#e2e8f0;padding:32px;border-radius:8px">
                  <h2 style="color:#10b981;margin:0 0 24px">New Project Inquiry</h2>
                  <table style="width:100%;border-collapse:collapse">
                    <tr><td style="padding:8px 0;color:#94a3b8;width:120px">Name</td><td style="padding:8px 0;color:#ffffff;font-weight:600">{data.name}</td></tr>
                    <tr><td style="padding:8px 0;color:#94a3b8">Email</td><td style="padding:8px 0"><a href="mailto:{data.email}" style="color:#10b981">{data.email}</a></td></tr>
                    <tr><td style="padding:8px 0;color:#94a3b8">Project Type</td><td style="padding:8px 0;color:#e2e8f0">{data.project_type or '—'}</td></tr>
                    <tr><td style="padding:8px 0;color:#94a3b8;vertical-align:top">Message</td><td style="padding:8px 0;color:#e2e8f0;line-height:1.6">{data.message}</td></tr>
                  </table>
                  <p style="margin:24px 0 0;font-size:12px;color:#475569">Tava One, LLC — tavaone.com</p>
                </div>
            """
        })

        return {"status": "ok"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
