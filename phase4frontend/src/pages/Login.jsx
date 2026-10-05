function Login() {
  const authServiceUrl = "http://localhost:8001";

  const loginWithGoogle = () => {
    window.location.href = `${authServiceUrl}/auth/google/login`;
  };

  const loginWithMicrosoft = () => {
    window.location.href = `${authServiceUrl}/auth/microsoft/login`;
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900">
            Mini Enterprise
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Enterprise Collaboration Platform
          </p>
        </div>

        <div className="mt-8 space-y-4">
          <button
            onClick={loginWithGoogle}
            className="flex w-full items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Continue with Google
          </button>

          <button
            onClick={loginWithMicrosoft}
            className="flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
          >
            Continue with Microsoft
          </button>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          Secured by Auth0
        </p>
      </div>
    </div>
  );
}

export default Login;
