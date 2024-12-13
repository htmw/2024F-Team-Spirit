import { useState } from "react";
import { useAuth } from "./AuthContext";
import { motion } from "framer-motion";
import { AlertCircle, Loader2 } from "lucide-react";

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const { login, signup, loginWithGoogle } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await signup(email, password);
      }
    } catch (err) {
      setError(getErrorMessage(err.code));
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError("");
    setIsGoogleLoading(true);
    try {
      await loginWithGoogle();
    } catch (err) {
      setError(getErrorMessage(err.code));
    } finally {
      setIsGoogleLoading(false);
    }
  };

  const getErrorMessage = (errorCode) => {
    switch (errorCode) {
      case "auth/invalid-email":
        return "Invalid email address";
      case "auth/user-disabled":
        return "This account has been disabled";
      case "auth/user-not-found":
        return "No account found with this email";
      case "auth/wrong-password":
        return "Incorrect password";
      case "auth/email-already-in-use":
        return "Email already in use";
      case "auth/operation-not-allowed":
        return "Operation not allowed";
      case "auth/weak-password":
        return "Password should be at least 6 characters";
      case "auth/popup-closed-by-user":
        return "Sign in was cancelled";
      case "auth/cancelled-popup-request":
        return "Only one sign in window allowed at a time";
      case "auth/popup-blocked":
        return "Sign in popup was blocked by the browser";
      default:
        return "An error occurred during authentication";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-gradient-to-b from-neutral-950 to-neutral-900 flex flex-col items-center justify-center p-4"
    >
      <div className="max-w-md w-full space-y-8">
        <motion.div
          initial={{ y: -20 }}
          animate={{ y: 0 }}
          className="text-center space-y-3"
        >
          <h1 className="text-5xl font-mono font-bold tracking-tight text-neutral-100">
            sentiment<span className="text-blue-500 animate-pulse">Pulse</span>
          </h1>
          <p className="text-neutral-400 text-sm font-mono bg-neutral-900/50 py-2 px-4 rounded-full inline-block">
            Market intelligence powered by sentiment analysis
          </p>
        </motion.div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-red-500/10 border border-red-500/50 text-red-500 px-4 py-3 rounded-lg text-sm font-mono flex items-center backdrop-blur-sm"
          >
            <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0 animate-pulse" />
            <span>{error}</span>
          </motion.div>
        )}

        <motion.div
          initial={{ scale: 0.95 }}
          animate={{ scale: 1 }}
          className="bg-neutral-900/80 border border-neutral-800 rounded-2xl p-8 backdrop-blur-xl shadow-xl"
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="text-xs font-mono text-neutral-400 uppercase tracking-wider">
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading || isGoogleLoading}
                className="w-full bg-neutral-800/50 border border-neutral-700 rounded-lg px-4 py-3 text-neutral-100 placeholder:text-neutral-600 focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 font-mono transition-all disabled:opacity-50"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-mono text-neutral-400 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading || isGoogleLoading}
                className="w-full bg-neutral-800/50 border border-neutral-700 rounded-lg px-4 py-3 text-neutral-100 placeholder:text-neutral-600 focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 font-mono transition-all disabled:opacity-50"
                required
              />
            </div>

            <motion.button
              type="submit"
              disabled={isLoading || isGoogleLoading}
              whileHover={{ scale: isLoading ? 1 : 1.02 }}
              whileTap={{ scale: isLoading ? 1 : 0.98 }}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-mono py-3 px-4 rounded-lg transition-colors uppercase tracking-wider shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : isLogin ? (
                "Sign In"
              ) : (
                "Create Account"
              )}
            </motion.button>
          </form>

          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-neutral-800"></div>
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-4 bg-neutral-900 text-neutral-500 font-mono uppercase tracking-wider">
                Or continue with
              </span>
            </div>
          </div>

          <motion.button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isLoading || isGoogleLoading}
            whileHover={{ scale: isGoogleLoading ? 1 : 1.02 }}
            whileTap={{ scale: isGoogleLoading ? 1 : 0.98 }}
            className="w-full bg-neutral-800 hover:bg-neutral-700 text-white font-mono py-3 px-4 rounded-lg transition-all flex items-center justify-center border border-neutral-700/50 shadow-lg hover:shadow-xl hover:border-neutral-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGoogleLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <img
                  src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Google_%22G%22_logo.svg/768px-Google_%22G%22_logo.svg.png"
                  alt="Google"
                  className="w-5 h-5 mr-3 transition-transform"
                />
                Google
              </>
            )}
          </motion.button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center"
        >
          <button
            onClick={() => setIsLogin(!isLogin)}
            disabled={isLoading || isGoogleLoading}
            className="text-neutral-400 hover:text-blue-400 text-sm font-mono transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLogin ? "Need an account?" : "Already have an account?"}
          </button>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default LoginPage;
