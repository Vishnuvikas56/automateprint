import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

interface User {
  user_id?: string;
  admin_id?: string;
  username: string;
  email: string;
  full_name?: string;
  balance?: number;
  store_id?: string;
  role?: string;
  contact_number?: string;
  address?: string;
  available?: boolean;
}

type UserRole = 'customer' | 'supervisor';

interface AuthContextType {
  user: User | null;
  token: string | null;
  userRole: UserRole | null;
  isAuthenticated: boolean;
  signin: (username: string, password: string, role: UserRole) => Promise<void>;
  signup: (email: string, username: string, password: string, role: UserRole, additionalData?: any) => Promise<void>;
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
  const [userRole, setUserRole] = useState<UserRole | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load token from localStorage on mount
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    const storedRole = localStorage.getItem('userRole') as UserRole | null;
    
    if (storedToken && storedUser && storedRole) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      setUserRole(storedRole);
      
      // Set default axios header
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
    }
    
    setLoading(false);
  }, []);

  const signin = async (username: string, password: string, role: UserRole) => {
    try {
      const endpoint = role === 'supervisor' 
        ? `${API_BASE_URL}/supervisor/signin`
        : `${API_BASE_URL}/auth/signin`;

      const response = await axios.post(endpoint, {
        username,
        password,
      });

      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      setUserRole(role);
      
      // Store in localStorage
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('userRole', role);
      
      // Set axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    } catch (error: any) {
      console.error('Signin error:', error);
      throw new Error(error.response?.data?.detail || 'Failed to sign in');
    }
  };

  const signup = async (
    email: string, 
    username: string, 
    password: string, 
    role: UserRole,
    additionalData?: any
  ) => {
    try {
      const endpoint = role === 'supervisor' 
        ? `${API_BASE_URL}/supervisor/signup`
        : `${API_BASE_URL}/auth/signup`;

      let requestData: any = {
        email,
        username,
        password,
      };

      // Add role-specific data
      if (role === 'supervisor') {
        requestData = {
          ...requestData,
          store_id: additionalData?.store_id,
          contact_number: additionalData?.contact_number,
          address: additionalData?.address,
          role: additionalData?.supervisorRole || 'OPERATOR',
        };
      } else {
        requestData.full_name = additionalData?.full_name;
      }

      const response = await axios.post(endpoint, requestData);

      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      setUserRole(role);
      
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('userRole', role);
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    } catch (error: any) {
      console.error('Signup error:', error);
      throw new Error(error.response?.data?.detail || 'Failed to sign up');
    }
  };

  const signout = () => {
    setUser(null);
    setToken(null);
    setUserRole(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('userRole');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        userRole,
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