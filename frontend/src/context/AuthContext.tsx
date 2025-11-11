import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

interface User {
  user_id: string;
  username: string;
  email: string;
  full_name?: string;
  balance?: number;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  signin: (username: string, password: string) => Promise<void>;
  signup: (email: string, username: string, password: string, full_name?: string) => Promise<void>;
  signout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load token from localStorage on mount
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      
      // Set default axios header
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
    }
    
    setLoading(false);
  }, []);

  const signin = async (username: string, password: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/signin`, {
        username,
        password,
      });

      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      
      // Store in localStorage
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      // Set axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    } catch (error: any) {
      console.error('Signin error:', error);
      throw new Error(error.response?.data?.detail || 'Failed to sign in');
    }
  };

  const signup = async (email: string, username: string, password: string, full_name?: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/signup`, {
        email,
        username,
        password,
        full_name,
      });

      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    } catch (error: any) {
      console.error('Signup error:', error);
      throw new Error(error.response?.data?.detail || 'Failed to sign up');
    }
  };

  const signout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        signin,
        signup,
        signout,
        loading,
      }}
    >
      {!loading && children}
    </AuthContext.Provider>
  );
};