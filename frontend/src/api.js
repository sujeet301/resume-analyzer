import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
  timeout: 120000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("resumeai_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && localStorage.getItem("resumeai_token")) {
      localStorage.removeItem("resumeai_token");
      localStorage.removeItem("resumeai_user");
      window.dispatchEvent(new Event("resumeai:logout"));
    }
    return Promise.reject(error);
  }
);

export const registerUser = (name, email, password) => api.post("/auth/register", {name, email, password});
export const loginUser = (email, password) => api.post("/auth/login", {email, password});
export const getMe = () => api.get("/auth/me");
export const deleteResume = (id) => api.delete(`/resumes/${id}`);

export const uploadResume = (file) => {
  const body = new FormData();
  body.append("file", file);
  return api.post("/resumes/upload", body, {headers:{"Content-Type":"multipart/form-data"}});
};
export const getResumes = () => api.get("/resumes");
export const getJobs = () => api.get("/jobs");
export const seedJobs = () => api.post("/jobs/seed");
export const getRecommendations = (id) => api.get(`/recommendations/${id}`);
export const getLiveJobs = (id, params={}) => api.get(`/jobs/search-live/${id}`, {params:{...params, providers:"arbeitnow"}});
export const getLinkedInLinks = (id, params={}) => api.get(`/jobs/linkedin-search/${id}`, {params});
export const analyzeResume = (resume_id, job_id) => api.post("/analysis", {resume_id, job_id});
export const aiResumeAnalysis = (resume_id, job_id=null) => api.post("/ai/resume-analysis", {resume_id, job_id});
export const startInterview = (resume_id, job_id, count=8) => api.post("/ai/interviews/start", {resume_id, job_id, count});
export const submitAnswer = (interview_id, question_index, answer) => api.post("/ai/interviews/answer", {interview_id, question_index, answer});
export const getInterview = (id) => api.get(`/ai/interviews/${id}`);
export const resumeChat = (resume_id, question, job_id=null) => api.post("/ai/resume-chat", {resume_id, question, job_id});
export const getAIStatus = () => api.get("/ai/status");
export const health = () => api.get("/health");
export default api;
