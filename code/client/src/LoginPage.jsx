import { useState } from "react";
import { useAuth } from "./AuthContext";
import { motion } from "framer-motion";
import { AlertCircle } from "lucide-react";

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login, signup, loginWithGoogle } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await signup(email, password);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center px-4">
      <div className="max-w-md w-full space-y-10 relative">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-mono font-bold tracking-tight text-neutral-100">
            sentiment<span className="text-blue-500">Pulse</span>
          </h1>
          <p className="text-neutral-400 text-sm font-mono">
            Market intelligence powered by sentiment analysis
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-500 px-4 py-3 rounded-lg text-sm font-mono flex items-center">
            <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-8 backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1">
              <label className="text-xs font-mono text-neutral-400">
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-3 text-neutral-100 placeholder:text-neutral-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/25 font-mono"
                required
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-mono text-neutral-400">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-3 text-neutral-100 placeholder:text-neutral-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/25 font-mono"
                required
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-mono py-3 px-4 rounded-lg transition-colors"
              >
                {isLogin ? "SIGN IN" : "CREATE ACCOUNT"}
              </button>
            </div>
          </form>

          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-neutral-800"></div>
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-2 bg-neutral-900 text-neutral-500 font-mono">
                OR CONTINUE WITH
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={loginWithGoogle}
            className="w-full bg-neutral-800 hover:bg-neutral-700 text-white font-mono py-3 px-4 rounded-lg transition-colors flex items-center justify-center group border border-neutral-700"
          >
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Google_%22G%22_logo.svg/768px-Google_%22G%22_logo.svg.png"
              alt="Google"
              className="w-5 h-5 mr-3"
            />
            GOOGLE
          </button>
        </div>

        <div className="text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-neutral-400 hover:text-neutral-300 text-sm font-mono"
          >
            {isLogin ? "Need an account?" : "Already have an account?"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
