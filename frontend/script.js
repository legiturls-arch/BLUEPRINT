
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";

import {
  getAuth,
  GoogleAuthProvider,
  GithubAuthProvider,
  signInWithPopup,
  RecaptchaVerifier,
  signInWithPhoneNumber
} from "https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js";

 const firebaseConfig = {
    apiKey: "AIzaSyDTn7L8vecBczFprpD0Rej_vQcuFPL39sM",
    authDomain: "blueprint-266f8.firebaseapp.com",
    projectId: "blueprint-266f8",
    storageBucket: "blueprint-266f8.firebasestorage.app",
    messagingSenderId: "329843617561",
    appId: "1:329843617561:web:482f8695d45956f50f9f88",
    measurementId: "G-DT0NZBQNCF"
  };


const LAB_URL = "/ui/builder.html";

const message = document.getElementById("login-message");
const phoneForm = document.getElementById("phone-form");
const otpSection = document.getElementById("otp-section");

let auth = null;
let confirmationResult = null;
let recaptchaVerifier = null;

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function ensureFirebase() {
  const configIsMissing = Object.values(firebaseConfig).some(
    value => !value || value.startsWith("PASTE_YOUR_")
  );

  if (configIsMissing) {
    throw new Error(
      "Firebase config is incomplete. Add your actual Firebase Web App API key."
    );
  }

  if (!auth) {
    const app = initializeApp(firebaseConfig);
    auth = getAuth(app);
  }

  return auth;
}

async function runSignIn(action) {
  const buttons = document.querySelectorAll(
    ".blueprint-login .login-provider"
  );

  buttons.forEach(button => {
    button.disabled = true;
  });

  showMessage("Please wait…");

  try {
    await action();
  } catch (error) {
    console.error("Blueprint sign-in error:", error);

    const messages = {
      "auth/popup-closed-by-user": "The sign-in window was closed.",
      "auth/popup-blocked": "Allow pop-ups and try again.",
      "auth/unauthorized-domain":
        "Add this domain to Firebase Authorized domains.",
      "auth/account-exists-with-different-credential":
        "An account already exists with another sign-in method.",
      "auth/invalid-phone-number":
        "Enter a valid phone number with country code.",
      "auth/invalid-verification-code":
        "The verification code is incorrect.",
      "auth/code-expired":
        "The verification code expired. Request a new one.",
      "auth/too-many-requests":
        "Too many attempts. Try again later.",
      "auth/operation-not-allowed":
        "Enable this sign-in provider in Firebase Console."
    };

    showMessage(
      messages[error.code] || error.message || "Sign-in failed.",
      true
    );
  } finally {
    buttons.forEach(button => {
      button.disabled = false;
    });
  }
}

function openLab() {
  window.location.assign(LAB_URL);
}

// Google sign-in
document.getElementById("google-btn").addEventListener("click", () => {
  runSignIn(async () => {
    const currentAuth = ensureFirebase();
    const provider = new GoogleAuthProvider();

    await signInWithPopup(currentAuth, provider);
    openLab();
  });
});

// GitHub sign-in
document.getElementById("github-btn").addEventListener("click", () => {
  runSignIn(async () => {
    const currentAuth = ensureFirebase();
    const provider = new GithubAuthProvider();

    await signInWithPopup(currentAuth, provider);
    openLab();
  });
});

// Show or hide phone login
document.getElementById("phone-toggle").addEventListener("click", () => {
  phoneForm.hidden = !phoneForm.hidden;
  showMessage("");
});

// Send phone verification code
document.getElementById("send-otp").addEventListener("click", () => {
  runSignIn(async () => {
    const currentAuth = ensureFirebase();
    const phone = document
      .getElementById("phone-number")
      .value.trim();

    if (!/^\+[1-9]\d{7,14}$/.test(phone)) {
      throw new Error(
        "Enter a valid phone number with country code, e.g. +919876543210."
      );
    }

    if (!recaptchaVerifier) {
      recaptchaVerifier = new RecaptchaVerifier(
        currentAuth,
        "recaptcha-container",
        { size: "normal" }
      );
    }

    await recaptchaVerifier.render();

    confirmationResult = await signInWithPhoneNumber(
      currentAuth,
      phone,
      recaptchaVerifier
    );

    otpSection.hidden = false;
    showMessage("Verification code sent. Check your phone.");
  });
});

// Verify OTP
document.getElementById("verify-otp").addEventListener("click", () => {
  runSignIn(async () => {
    if (!confirmationResult) {
      throw new Error("Request a verification code first.");
    }

    const code = document.getElementById("otp-code").value.trim();

    if (!/^\d{6}$/.test(code)) {
      throw new Error("Enter the 6-digit verification code.");
    }

    await confirmationResult.confirm(code);
    openLab();
  });
});
