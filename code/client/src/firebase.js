// firebase.js
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBaaPr1xkDG7sBEyEzZXe8ftvtr58oPikY",
  authDomain: "sentimentplus-1485b.firebaseapp.com",
  projectId: "sentimentplus-1485b",
  storageBucket: "sentimentplus-1485b.firebasestorage.app",
  messagingSenderId: "671955364996",
  appId: "1:671955364996:web:ab7606c92d8cdd6e7526d1",
  measurementId: "G-9Q0ER5QJCK",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
