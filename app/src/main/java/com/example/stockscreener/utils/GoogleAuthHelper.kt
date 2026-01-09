package com.example.stockscreener.utils

import android.app.Activity
import android.content.Intent
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider

class GoogleAuthHelper (private val activity: Activity){//val represnt the android screen we are working..
private val auth: FirebaseAuth = FirebaseAuth.getInstance()
    private lateinit var googleSignInClient: GoogleSignInClient
//hold your Google Sign-In client, which is used to let users log in with their Google account.
fun setupGoogleSignIn(): GoogleSignInClient {
    val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
        .requestIdToken("26950318537-024gotvr0uvmgc6hfpomhcfulu4osi0e.apps.googleusercontent.com") // Replace with your web client ID
        .requestEmail()
        .build()

    googleSignInClient = GoogleSignIn.getClient(activity, gso)
    return googleSignInClient
}
    fun handleSignInResult(data: Intent?, onSuccess: (String?) -> Unit, onFailure: (String) -> Unit) {
        val task = GoogleSignIn.getSignedInAccountFromIntent(data)
        try {
            val account = task.getResult(ApiException::class.java)
            firebaseAuthWithGoogle(account.idToken!!, onSuccess, onFailure)
        } catch (e: ApiException) {
            onFailure("Google sign-in failed: ${e.message}")
        }
    }

    private fun firebaseAuthWithGoogle(idToken: String, onSuccess: (String?) -> Unit, onFailure: (String) -> Unit) {
        val credential = GoogleAuthProvider.getCredential(idToken, null)
        auth.signInWithCredential(credential)
            .addOnCompleteListener(activity) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    onSuccess(user?.displayName)
                } else {
                    onFailure(task.exception?.message ?: "Authentication failed")
                }
            }
    }
}