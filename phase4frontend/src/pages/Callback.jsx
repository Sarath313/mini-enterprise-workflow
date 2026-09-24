import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function Callback() {
  const navigate = useNavigate();

  const [message, setMessage] = useState(
    "Completing authentication..."
  );

  useEffect(() => {
    const processCallback = () => {
      try {
        /*
         * Auth Service redirects to:
         * http://localhost:5173/callback#access_token=...
         */

        const hash = window.location.hash.substring(1);

        const params = new URLSearchParams(hash);

        const accessToken = params.get("access_token");

        if (!accessToken) {
          setMessage(
            "Authentication failed. Access token was not found."
          );
          return;
        }

        // Store Auth0 access token
        localStorage.setItem(
          "access_token",
          accessToken
        );

        // Remove token from the visible browser URL
        window.history.replaceState(
          {},
          document.title,
          "/callback"
        );

        // Go to protected dashboard
        navigate("/dashboard", {
          replace: true,
        });
      } catch (error) {
        console.error(
          "OAuth callback error:",
          error
        );

        setMessage(
          "Authentication failed. Please try again."
        );
      }
    };

    processCallback();
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-xl">
        <div className="mx-auto mb-5 h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />

        <h1 className="text-xl font-bold text-slate-900">
          Authentication
        </h1>

        <p className="mt-2 text-sm text-slate-500">
          {message}
        </p>
      </div>
    </div>
  );
}

export default Callback;