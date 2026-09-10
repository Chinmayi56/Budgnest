import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Wallet, Eye, EyeOff } from "lucide-react";

const API = (import.meta.env.VITE_API_URL || "http://localhost:8001/api").replace(/\/$/, "");

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [confirm, setConfirm] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const request = async (path, body) => {
    const res = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || "Something went wrong");
    return data;
  };
  const finishLogin = (data) => { localStorage.setItem("budgetnest_token", data.access_token); localStorage.setItem("budgetnest_user", JSON.stringify(data.user)); navigate("/dashboard"); };
  const submitPassword = async (e) => { e.preventDefault(); setError(""); setLoading(true); try { finishLogin(await request("/auth/login", { email, password })); } catch (e) { setError(e.message); } finally { setLoading(false); } };
  const sendCode = async () => { setError(""); setMessage(""); if (!email) return setError("Please enter your email address"); setLoading(true); try { const d = await request("/auth/send-login-code", { email }); setSent(true); setMessage(d.message || "Verification code sent"); } catch (e) { setError(e.message); } finally { setLoading(false); } };
  const verifyCode = async (e) => { e.preventDefault(); setError(""); setLoading(true); try { finishLogin(await request("/auth/verify-login-code", { email, code })); } catch (e) { setError(e.message); } finally { setLoading(false); } };
  const register = async (e) => { e.preventDefault(); setError(""); setMessage(""); if (password !== confirm) return setError("Passwords do not match"); setLoading(true); try { await request("/auth/register", { full_name: name, email, password }); setMessage("Account created successfully. You can now sign in."); setMode("signin"); setPassword(""); setConfirm(""); } catch (e) { setError(e.message); } finally { setLoading(false); } };
  const switchMode = (m) => { setMode(m); setError(""); setMessage(""); if (m !== "code") setSent(false); };

  const input = "w-full rounded-lg border border-border px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300";
  return <div className="min-h-screen flex items-center justify-center bg-paper px-4 py-8"><div className="w-full max-w-md">
    <div className="flex flex-col items-center mb-6"><div className="h-12 w-12 rounded-xl2 bg-brand-500 flex items-center justify-center mb-3 shadow-card"><Wallet className="text-white" size={22}/></div><h1 className="text-2xl font-display font-semibold text-ink">BudgetNest</h1><p className="text-sm text-ink/50 mt-1 text-center">Manage your money securely.</p></div>
    <div className="bg-surface border border-border rounded-xl2 shadow-card p-6"><div className="grid grid-cols-3 gap-1 mb-5 bg-paper p-1 rounded-lg"><button onClick={()=>switchMode("signin")} className={`py-2 text-sm rounded-md ${mode==="signin"?"bg-white shadow text-ink":"text-ink/50"}`}>Sign In</button><button onClick={()=>switchMode("code")} className={`py-2 text-sm rounded-md ${mode==="code"?"bg-white shadow text-ink":"text-ink/50"}`}>Email Code</button><button onClick={()=>switchMode("signup")} className={`py-2 text-sm rounded-md ${mode==="signup"?"bg-white shadow text-ink":"text-ink/50"}`}>Sign Up</button></div>
    {error && <p className="mb-4 text-sm text-red-600">{error}</p>}{message && <p className="mb-4 text-sm text-green-600">{message}</p>}
    {mode === "signin" && <form onSubmit={submitPassword} className="space-y-4"><Field label="Email" type="email" value={email} setValue={setEmail} cls={input}/><div><label className="block text-sm font-medium text-ink/70 mb-1.5">Password</label><div className="relative"><input required type={showPassword?"text":"password"} value={password} onChange={e=>setPassword(e.target.value)} className={`${input} pr-10`} placeholder="••••••••"/><button type="button" onClick={()=>setShowPassword(!showPassword)} className="absolute right-3 top-3 text-ink/50">{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></div><Button loading={loading}>Sign In</Button></form>}
    {mode === "code" && (!sent ? <div className="space-y-4"><Field label="Registered Email" type="email" value={email} setValue={setEmail} cls={input}/><Button loading={loading} onClick={sendCode}>Send 6-Digit Code</Button></div> : <form onSubmit={verifyCode} className="space-y-4"><p className="text-sm text-ink/60">We sent a 6-digit code to <b>{email}</b>.</p><Field label="Verification Code" value={code} setValue={v=>setCode(v.replace(/\D/g, "").slice(0,6))} cls={`${input} text-center tracking-[0.5em]`} placeholder="000000" inputMode="numeric" maxLength={6}/><Button loading={loading} disabled={code.length!==6}>Verify & Sign In</Button><button type="button" disabled={loading} onClick={sendCode} className="w-full text-sm text-brand-600 hover:underline">Resend Code</button><button type="button" onClick={()=>setSent(false)} className="w-full text-xs text-ink/50">Change Email</button></form>)}
    {mode === "signup" && <form onSubmit={register} className="space-y-4"><Field label="Full Name" value={name} setValue={setName} cls={input}/><Field label="Email" type="email" value={email} setValue={setEmail} cls={input}/><div><label className="block text-sm font-medium text-ink/70 mb-1.5">Password</label><div className="relative"><input required minLength={8} type={showSignupPassword?"text":"password"} value={password} onChange={e=>setPassword(e.target.value)} className={`${input} pr-10`} placeholder="••••••••"/><button type="button" onClick={()=>setShowSignupPassword(!showSignupPassword)} className="absolute right-3 top-3 text-ink/50" aria-label={showSignupPassword?"Hide password":"Show password"}>{showSignupPassword?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></div><div><label className="block text-sm font-medium text-ink/70 mb-1.5">Confirm Password</label><div className="relative"><input required minLength={8} type={showConfirmPassword?"text":"password"} value={confirm} onChange={e=>setConfirm(e.target.value)} className={`${input} pr-10`} placeholder="••••••••"/><button type="button" onClick={()=>setShowConfirmPassword(!showConfirmPassword)} className="absolute right-3 top-3 text-ink/50" aria-label={showConfirmPassword?"Hide password":"Show password"}>{showConfirmPassword?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></div><Button loading={loading}>Create Account</Button></form>}
    </div></div></div>;
}
function Field({label, value, setValue, cls, type="text", ...props}) { return <div><label className="block text-sm font-medium text-ink/70 mb-1.5">{label}</label><input required type={type} value={value} onChange={e=>setValue(e.target.value)} className={cls} {...props}/></div>; }
function Button({children, loading, disabled, onClick}) { return <button type={onClick?"button":"submit"} onClick={onClick} disabled={loading||disabled} className="w-full bg-brand-500 hover:bg-brand-600 disabled:opacity-60 text-white font-medium py-2.5 rounded-lg transition-colors">{loading?"Please wait...":children}</button>; }
