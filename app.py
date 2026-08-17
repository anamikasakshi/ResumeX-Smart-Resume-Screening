from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
import re, io, os, json, urllib.request, urllib.error
from pypdf import PdfReader
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(
    __name__,
    static_folder="public/static",
    static_url_path="/static"
)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
ALLOWED = {".pdf", ".docx", ".txt"}
SKILLS = ["python","java","c++","c","javascript","typescript","react","node.js","express","html","css","sql","mysql","postgresql","mongodb","spring boot","django","flask","fastapi","android","kotlin","flutter","dart","git","github","docker","kubernetes","aws","azure","gcp","machine learning","deep learning","nlp","natural language processing","generative ai","genai","llm","rag","tensorflow","pytorch","scikit-learn","pandas","numpy","opencv","data analysis","power bi","tableau","rest api","graphql","figma","linux","cybersecurity","computer vision","data structures","algorithms"]

def extract_text(filename, data):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED: raise ValueError("Unsupported file type")
    if ext == ".pdf": return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
    if ext == ".docx": return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    return data.decode("utf-8", errors="ignore")

def normalize(text): return re.sub(r"\s+", " ", text.lower()).strip()

def find_skills(text):
    t=normalize(text); return sorted({s for s in SKILLS if re.search(r"(?<!\w)"+re.escape(s.lower())+r"(?!\w)",t)})

def extract_contact(text):
    email=re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+",text)
    phone=re.search(r"(?:\+91[\s-]?)?[6-9]\d{9}",re.sub(r"[().]","",text))
    return {"email":email.group(0) if email else "","phone":phone.group(0) if phone else ""}

def extract_experience(text):
    t=normalize(text); values=[]
    for p in [r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",r"experience\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)"]: values += [float(x) for x in re.findall(p,t)]
    return max(values) if values else 0

def chunks(text,size=90):
    words=normalize(text).split(); return [" ".join(words[i:i+size]) for i in range(0,len(words),size)] or [""]

def retrieve_context(job_text,resume_text,k=3):
    parts=chunks(resume_text); 
    if len(parts)==1: return parts
    v=TfidfVectorizer(stop_words="english",ngram_range=(1,2)); m=v.fit_transform([normalize(job_text)]+parts)
    scores=cosine_similarity(m[0:1],m[1:]).flatten()
    return [parts[i] for i in scores.argsort()[::-1][:k]]

def call_ollama(prompt):
    model=os.getenv("OLLAMA_MODEL","").strip()
    if not model: return None
    payload=json.dumps({"model":model,"prompt":prompt,"stream":False}).encode()
    req=urllib.request.Request("http://127.0.0.1:11434/api/generate",data=payload,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=25) as r: return json.loads(r.read().decode()).get("response","").strip() or None
    except (urllib.error.URLError,TimeoutError,json.JSONDecodeError): return None

def deterministic_explanation(c):
    matched=c["matched_skills"]; missing=c["missing_skills"]; strengths=[]
    if matched: strengths.append(f"matches {len(matched)} detected role skills, including {', '.join(matched[:5])}")
    if c["experience_years"]: strengths.append(f"shows about {c['experience_years']:g} year(s) of experience")
    strengths.append("strong semantic overlap" if c["match"]>=70 else "moderate semantic overlap" if c["match"]>=45 else "limited semantic overlap")
    why="WHY THIS RANK\nThe candidate scores %s%% because %s."%(c["score"],"; ".join(strengths))
    gaps="GAPS\n"+("No major skill gaps were detected from the configured skill dictionary." if not missing else "Potential gaps: "+", ".join(missing[:8])+".")
    focus="INTERVIEW FOCUS\nVerify the strongest matched skills with a short practical task and ask about any missing role requirements."
    return why+"\n\n"+gaps+"\n\n"+focus

def genai_explanation(c,job_text,context):
    evidence="\n---\n".join(context)[:7000]
    prompt=("You are an AI recruiting assistant for an academic prototype. Do not infer protected traits or make a final hiring decision. "
            "Explain the ranking only from the supplied evidence. Return exactly three short sections: WHY THIS RANK, GAPS, INTERVIEW FOCUS. "
            "Keep each section under 70 words.\n\nJOB:\n"+job_text[:5000]+"\n\nMETRICS: overall="+str(c["score"])+"%, relevance="+str(c["match"])+"%, skills="+str(c["skill_score"])+"%, experience="+str(c["experience_score"])+"%.\n"
            "MATCHED SKILLS: "+", ".join(c["matched_skills"])+"\nMISSING: "+", ".join(c["missing_skills"])+"\nRESUME EVIDENCE:\n"+evidence)
    return call_ollama(prompt) or deterministic_explanation(c)

def score_candidates(job_text,candidates):
    corpus=[normalize(job_text)]+[normalize(c["text"]) for c in candidates]
    v=TfidfVectorizer(stop_words="english",ngram_range=(1,2),max_features=8000); m=v.fit_transform(corpus)
    sims=cosine_similarity(m[0:1],m[1:]).flatten(); job_skills=set(find_skills(job_text)); job_years=extract_experience(job_text); results=[]
    for i,c in enumerate(candidates):
        cs=set(find_skills(c["text"])); matched=sorted(job_skills&cs); missing=sorted(job_skills-cs); skill=(len(matched)/len(job_skills)*100) if job_skills else 50; rel=float(sims[i]*100); exp=extract_experience(c["text"]); exp_score=min(exp/job_years,1)*100 if job_years else (min(exp/5,1)*100 if exp else 50); final=rel*.45+skill*.35+exp_score*.20
        results.append({"name":c["name"],"file":c["file"],"text":c["text"],"score":round(final,1),"match":round(rel,1),"skill_score":round(skill,1),"experience_score":round(exp_score,1),"experience_years":exp,"matched_skills":matched,"missing_skills":missing,"contact":extract_contact(c["text"])})
    results.sort(key=lambda x:x["score"],reverse=True)
    for rank,c in enumerate(results,1): c["rank"]=rank
    return results,sorted(job_skills)

@app.get("/")
def index(): return render_template("index.html")

@app.post("/api/rank")
def rank():
    job_text=request.form.get("job_description","").strip(); uploads=request.files.getlist("resumes")
    if not job_text: return jsonify({"error":"Please provide a job description."}),400
    if not uploads: return jsonify({"error":"Upload at least one resume."}),400
    candidates=[]; errors=[]
    for file in uploads:
        if not file or not file.filename: continue
        filename=secure_filename(file.filename)
        try:
            text=extract_text(filename,file.read())
            if len(text.strip())<20: raise ValueError("Very little readable text was found.")
            candidates.append({"name":Path(filename).stem.replace("_"," ").replace("-"," ").title(),"file":filename,"text":text})
        except Exception as exc: errors.append({"file":filename,"error":str(exc)})
    if not candidates: return jsonify({"error":"No readable resumes were found.","errors":errors}),400
    results,job_skills=score_candidates(job_text,candidates)
    for c in results:
        context=retrieve_context(job_text,c["text"]); c["ai_explanation"]=genai_explanation(c,job_text,context); c["evidence"]=context[:3]; c.pop("text",None)
    return jsonify({"results":results,"job_skills":job_skills,"processed":len(candidates),"errors":errors,"genai_mode":bool(os.getenv("OLLAMA_MODEL"))})

@app.post("/api/explain")
def explain():
    data=request.get_json(force=True); job=data.get("job_description",""); c=data.get("candidate")
    if not job or not c: return jsonify({"error":"Missing job or candidate data."}),400
    return jsonify({"explanation":genai_explanation(c,job,data.get("evidence") or [])})

@app.errorhandler(413)
def too_large(_): return jsonify({"error":"A file is too large. Maximum size is 10 MB."}),413

if __name__=="__main__": app.run(debug=True)
