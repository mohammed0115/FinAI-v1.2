"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
    Sparkles,
    Shield,
    TrendingUp,
    Globe2,
    Zap,
    ArrowRight,
    Eye,
    EyeOff,
    AlertCircle,
    Lock,
} from "lucide-react";

export default function Login() {
    const t = useTranslations();
    const locale = useLocale();
    const isRTL = locale === "ar";
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        // Simulate login - will be replaced with actual API call
        setTimeout(() => {
            window.location.href = `/${locale}/dashboard`;
        }, 1000);
    };

    return (
        <div className={`min-h-screen w-full relative overflow-x-hidden bg-gradient-to-br from-gray-50 via-gray-200 to-gray-400 ${isRTL ? "rtl text-right" : "ltr text-left"}`} dir={isRTL ? "rtl" : "ltr"}>
            {/* Animated background elements */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute -top-40 -end-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl animate-pulse"></div>
                <div className="absolute top-1/2 -start-40 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }}></div>
                <div className="absolute bottom-0 end-1/3 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "0.5s" }}></div>
            </div>

            {/* Grid overlay */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#00000008_1px,transparent_1px),linear-gradient(to_bottom,#00000008_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>

            <div className={`relative z-10 min-h-screen flex ${isRTL ? "flex-row-reverse" : ""}`}>
                {/* Top-right language toggle */}
                <div className={`absolute ${isRTL ? "top-6 left-8 md:top-8 md:left-10" : "top-6 right-8 md:top-8 md:right-10"} z-50`}>
                    <Link
                        href="/login"
                        locale={isRTL ? "en" : "ar"}
                        className="px-4 py-2 bg-white/60 backdrop-blur-sm border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-white/80 transition-all"
                    >
                        {isRTL ? "English" : "العربية"}
                    </Link>
                </div>

                {/* Left Panel - Branding */}
                <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-16 pt-32 text-gray-800">
                    <div>
                        <div className={`flex items-center gap-4 mb-16 ${isRTL ? "flex-row-reverse" : ""}`}>
                            <div className="relative">
                                <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/50">
                                    <Sparkles className="w-7 h-7 text-white" />
                                </div>
                                <div className="absolute -top-1 -end-1 w-3 h-3 bg-green-400 rounded-full border-2 border-slate-950"></div>
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
                                    GSC‑FinAI
                                </h1>
                                <p className="text-xs text-gray-600">{isRTL ? "منصة التمويل الذكية" : "Intelligent Finance Platform"}</p>
                            </div>
                        </div>

                        <div className="space-y-10">
                            <h2 className="text-5xl font-bold leading-tight">
                                {isRTL ? "إدارة مالية" : "Smart Financial"}<br />
                                {isRTL ? "ذكية لأسواق" : "Management for"}<br />
                                <span className="bg-gradient-to-r from-blue-600 via-cyan-600 to-purple-600 bg-clip-text text-transparent">
                                    {isRTL ? "دول مجلس التعاون" : "GCC Markets"}
                                </span>
                            </h2>
                            <p className="text-lg text-gray-700 max-w-md leading-relaxed">
                                {isRTL
                                    ? "معالجة المستندات بالذكاء الاصطناعي، وأتمتة الامتثال، ورؤى مالية في الوقت الفعلي مصممة خصيصاً لشركات مجلس التعاون الخليجي."
                                    : "AI-powered document processing, compliance automation, and real-time financial insights tailored for Gulf Cooperation Council businesses."
                                }
                            </p>
                        </div>
                    </div>

                    {/* Large Animated Visualization */}
                    <div className="my-14 relative h-36">
                        {/* Animated Progress Bars */}
                        <div className="space-y-5">
                            <div className="space-y-2.5">
                                <div className="flex items-center justify-between text-xs text-gray-600">
                                    <span className={`flex items-center gap-2 ${isRTL ? "flex-row-reverse" : ""}`}>
                                        <TrendingUp className="w-4 h-4" />
                                        {isRTL ? "قوة المعالجة بالذكاء الاصطناعي" : "AI Processing Power"}
                                    </span>
                                    <span className="font-semibold">94%</span>
                                </div>
                                <div className="h-2.5 bg-white/5 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-blue-500 via-cyan-400 to-blue-500 rounded-full animate-shimmer bg-[length:200%_100%]"
                                        style={{ width: "94%" }}
                                    ></div>
                                </div>
                            </div>

                            <div className="space-y-2.5">
                                <div className="flex items-center justify-between text-xs text-gray-600">
                                    <span className={`flex items-center gap-2 ${isRTL ? "flex-row-reverse" : ""}`}>
                                        <Shield className="w-4 h-4" />
                                        {isRTL ? "نقاط الأمان" : "Security Score"}
                                    </span>
                                    <span className="font-semibold">99%</span>
                                </div>
                                <div className="h-2.5 bg-white/5 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-green-500 via-emerald-400 to-green-500 rounded-full animate-shimmer-delay1 bg-[length:200%_100%]"
                                        style={{ width: "99%" }}
                                    ></div>
                                </div>
                            </div>

                            <div className="space-y-2.5">
                                <div className="flex items-center justify-between text-xs text-gray-600">
                                    <span className={`flex items-center gap-2 ${isRTL ? "flex-row-reverse" : ""}`}>
                                        <Zap className="w-4 h-4" />
                                        {isRTL ? "كفاءة الأتمتة" : "Automation Efficiency"}
                                    </span>
                                    <span className="font-semibold">97%</span>
                                </div>
                                <div className="h-2.5 bg-white/5 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-purple-500 via-pink-400 to-purple-500 rounded-full animate-shimmer-delay2 bg-[length:200%_100%]"
                                        style={{ width: "97%" }}
                                    ></div>
                                </div>
                            </div>
                        </div>

                        {/* Floating Stats */}
                        <div className="absolute -end-4 top-0 animate-float">
                            <div className="bg-white/60 backdrop-blur-sm border border-gray-300 rounded-lg px-4 py-3 shadow-lg">
                                <div className="text-2xl font-bold text-gray-800">500+</div>
                                <div className="text-xs text-gray-600">{isRTL ? "مستخدم نشط" : "Active Users"}</div>
                            </div>
                        </div>

                        <div className="absolute -start-4 bottom-0 animate-float-delay">
                            <div className="bg-white/60 backdrop-blur-sm border border-gray-300 rounded-lg px-4 py-3 shadow-lg">
                                <div className="text-2xl font-bold text-gray-800">99.9%</div>
                                <div className="text-xs text-gray-600">{isRTL ? "وقت التشغيل" : "Uptime"}</div>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-5">
                        <div className="bg-white/40 backdrop-blur-sm border border-gray-200 rounded-xl p-5 transition-all duration-300 hover:bg-white/60 hover:border-gray-300 hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20 cursor-pointer group">
                            <Shield className="w-10 h-10 text-blue-600 mb-3 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3" />
                            <h3 className="font-semibold text-base mb-1.5">{isRTL ? "متوافق مع GCC" : "GCC Compliant"}</h3>
                            <p className="text-xs text-gray-600 leading-relaxed">{isRTL ? "جاهز لـ ZATCA وضريبة القيمة المضافة" : "ZATCA & VAT Ready"}</p>
                        </div>
                        <div className="bg-white/40 backdrop-blur-sm border border-gray-200 rounded-xl p-5 transition-all duration-300 hover:bg-white/60 hover:border-gray-300 hover:scale-105 hover:shadow-lg hover:shadow-cyan-500/20 cursor-pointer group">
                            <TrendingUp className="w-10 h-10 text-cyan-600 mb-3 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3" />
                            <h3 className="font-semibold text-base mb-1.5">{isRTL ? "تحليلات الذكاء الاصطناعي" : "AI Analytics"}</h3>
                            <p className="text-xs text-gray-600 leading-relaxed">{isRTL ? "رؤى تنبؤية" : "Predictive Insights"}</p>
                        </div>
                        <div className="bg-white/40 backdrop-blur-sm border border-gray-200 rounded-xl p-5 transition-all duration-300 hover:bg-white/60 hover:border-gray-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/20 cursor-pointer group">
                            <Globe2 className="w-10 h-10 text-purple-600 mb-3 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3" />
                            <h3 className="font-semibold text-base mb-1.5">{isRTL ? "متعدد اللغات" : "Multilingual"}</h3>
                            <p className="text-xs text-gray-600 leading-relaxed">{isRTL ? "العربية والإنجليزية" : "Arabic & English"}</p>
                        </div>
                        <div className="bg-white/40 backdrop-blur-sm border border-gray-200 rounded-xl p-5 transition-all duration-300 hover:bg-white/60 hover:border-gray-300 hover:scale-105 hover:shadow-lg hover:shadow-yellow-500/20 cursor-pointer group">
                            <Zap className="w-10 h-10 text-yellow-600 mb-3 transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3" />
                            <h3 className="font-semibold text-base mb-1.5">{isRTL ? "OCR/HDR" : "OCR/HDR"}</h3>
                            <p className="text-xs text-gray-600 leading-relaxed">{isRTL ? "استخراج ذكي" : "Smart Extraction"}</p>
                        </div>
                    </div>
                </div>

                {/* Right Panel - Login Form */}
                <div className="flex-1 flex items-center justify-center px-6 md:px-8 pt-24 lg:pt-8 pb-32">
                    <div className="w-full max-w-xl">
                        {/* Mobile Logo */}
                        <div className={`lg:hidden flex items-center justify-center gap-3 mb-10 ${isRTL ? "flex-row-reverse" : ""}`}>
                            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/50">
                                <Sparkles className="w-6 h-6 text-white" />
                            </div>
                            <h1 className="text-2xl font-bold text-gray-800">GSC‑FinAI</h1>
                        </div>

                        <div className="bg-white/60 backdrop-blur-xl border border-gray-200 rounded-2xl p-8 md:p-10 shadow-2xl">
                            <div className="mb-8">
                                <h2 className="text-2xl md:text-3xl font-bold text-gray-800 mb-3">
                                    {isRTL ? "مرحباً بعودتك" : "Welcome back"}
                                </h2>
                                <p className="text-gray-700 text-base">
                                    {isRTL ? "قم بتسجيل الدخول للوصول إلى لوحة التحكم المالية" : "Sign in to access your financial dashboard"}
                                </p>
                            </div>

                            <form onSubmit={handleLogin} className="space-y-6">
                                {error && (
                                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3">
                                        <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <p className="text-sm text-red-700 font-medium">{isRTL ? "فشل تسجيل الدخول" : "Login Failed"}</p>
                                            <p className="text-sm text-red-600 mt-1">{error}</p>
                                        </div>
                                    </div>
                                )}

                                <div className="space-y-2.5">
                                    <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                                        {isRTL ? "عنوان البريد الإلكتروني" : "Email Address"}
                                    </label>
                                    <input
                                        id="email"
                                        type="email"
                                        placeholder={isRTL ? "your.email@company.com" : "your.email@company.com"}
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full bg-white/80 border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all h-12 px-4 text-base rounded-xl outline-none"
                                        autoComplete="email"
                                        required
                                    />
                                </div>

                                <div className="space-y-2.5">
                                    <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                                        {isRTL ? "كلمة المرور" : "Password"}
                                    </label>
                                    <div className="relative">
                                        <input
                                            id="password"
                                            type={showPassword ? "text" : "password"}
                                            placeholder="••••••••"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            className="w-full bg-white/80 border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all h-12 px-4 pl-12 text-base rounded-xl outline-none"
                                            autoComplete="current-password"
                                            required
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-800 transition-colors"
                                        >
                                            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                        </button>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between text-sm pt-2">
                                    <label className={`flex items-center gap-2 text-gray-600 cursor-pointer hover:text-gray-800 transition-colors ${isRTL ? "flex-row-reverse" : ""}`}>
                                        <input type="checkbox" className="w-4 h-4 rounded border-gray-300 bg-white text-blue-500 focus:ring-blue-500 focus:ring-offset-0" />
                                        <span>{isRTL ? "تذكرني" : "Remember me"}</span>
                                    </label>
                                    <button type="button" className="text-blue-600 hover:text-blue-700 transition-colors font-medium">
                                        {isRTL ? "نسيت كلمة المرور؟" : "Forgot password?"}
                                    </button>
                                </div>

                                {/* Security verification bypass notice */}
                                <div className="text-center text-xs text-green-600 pt-2">
                                    ✓ {isRTL ? "تم تجاوز التحقق الأمني (وضع التطوير)" : "Security verification bypassed (Development Mode)"}
                                </div>

                                <button
                                    type="submit"
                                    disabled={isLoading}
                                    className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-semibold h-12 rounded-xl shadow-lg shadow-blue-500/30 transition-all hover:shadow-blue-500/50 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                    {isLoading ? (
                                        <div className="flex items-center justify-center gap-2">
                                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                            <span className="text-base">{isRTL ? "جارِ تسجيل الدخول..." : "Signing in..."}</span>
                                        </div>
                                    ) : (
                                        <div className={`flex items-center justify-center gap-2 ${isRTL ? "flex-row-reverse" : "flex-row"}`}>
                                            <span className="text-base">{isRTL ? "تسجيل الدخول" : "Sign In"}</span>
                                            <ArrowRight className={`w-5 h-5 ${isRTL ? "rotate-180" : ""}`} />
                                        </div>
                                    )}
                                </button>

                                <div className="relative my-6">
                                    <div className="absolute inset-0 flex items-center">
                                        <div className="w-full border-t border-gray-300"></div>
                                    </div>
                                    <div className="relative flex justify-center text-xs">
                                        <span className="px-4 py-1 bg-white/70 text-gray-600 uppercase tracking-wider">
                                            {isRTL ? "وضع التطوير" : "Development Mode"}
                                        </span>
                                    </div>
                                </div>

                                <div className="bg-amber-100/60 border border-amber-300/60 rounded-xl p-4 text-center space-y-2">
                                    <p className={`text-sm text-amber-800 font-semibold flex items-center justify-center gap-2 ${isRTL ? "flex-row-reverse" : ""}`}>
                                        <Lock className="w-4 h-4" />
                                        {isRTL ? "بيئة تجريبية" : "License Required"}
                                    </p>
                                    <p className="text-xs text-amber-700 leading-relaxed">
                                        {isRTL
                                            ? "يتطلب حسابك ترخيصاً صالحاً للوصول إلى النظام. اتصل بالمسؤول إذا كنت بحاجة إلى ترخيص."
                                            : "Your account requires a valid license to access the system. Contact your administrator if you need a license."
                                        }
                                    </p>
                                </div>

                                <p className="text-center text-base text-gray-600 pt-4">
                                    {isRTL ? "ليس لديك حساب؟" : "Don't have an account?"}{" "}
                                    <Link href="/signup" className="text-blue-600 hover:text-blue-700 font-semibold transition-colors">
                                        {isRTL ? "سجل مجاناً" : "Sign Up for Free"}
                                    </Link>
                                </p>
                            </form>
                        </div>

                        <p className="text-center text-sm text-gray-600 mt-8 leading-relaxed">
                            {isRTL
                                ? "© 2025 GSC-FinAI. مدعوم بالذكاء الاصطناعي للتميز المالي في دول الخليج."
                                : "© 2025 GSC-FinAI. Powered by AI for GCC Financial Excellence."
                            }
                        </p>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <footer className="absolute bottom-0 start-0 end-0 py-2 text-center z-10 pointer-events-none">
                <div className="text-sm text-gray-600 pointer-events-auto leading-relaxed">
                    © {new Date().getFullYear()} GSC-FinAI. {isRTL ? "جميع الحقوق محفوظة لـ" : "All rights reserved for"}{" "}
                    <a
                        href="https://www.gscompany.sa"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-700 font-semibold transition-colors underline-offset-2 hover:underline cursor-pointer"
                    >
                        GetSolution Co.
                    </a>
                </div>
            </footer>
</div>
    );
}


