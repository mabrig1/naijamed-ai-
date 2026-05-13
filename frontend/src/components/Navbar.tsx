import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Navbar() {
  const { isAuthenticated, logout, user } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <Link to="/" className="text-xl font-bold text-brand-700">
        🌿 NigerFlora BioSciences
      </Link>
      <div className="flex items-center gap-4">
        {isAuthenticated ? (
          <>
            <Link to="/dashboard" className="text-sm font-medium text-gray-600 hover:text-brand-700">
              Dashboard
            </Link>
            <Link to="/help" className="text-sm font-medium text-gray-600 hover:text-brand-700">
              Help
            </Link>
            {user?.role === "admin" && (
              <Link
                to="/admin"
                className="text-sm font-medium text-amber-600 hover:text-amber-800 font-semibold"
              >
                ⚙ Admin
              </Link>
            )}
            <button
              onClick={handleLogout}
              className="text-sm font-medium text-red-600 hover:text-red-800"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/help" className="text-sm font-medium text-gray-600 hover:text-brand-700">
              Help
            </Link>
            <Link
              to="/login"
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              Sign In
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
