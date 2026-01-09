package com.example.stockscreener.Screens

import android.R.attr.contentDescription
import android.app.Activity
import android.widget.Space
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonColors
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ModifierLocalBeyondBoundsLayout
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.example.stockscreener.R
import com.example.stockscreener.utils.GoogleAuthHelper
import com.google.firebase.auth.FirebaseAuth

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(navController: NavController){
    //NavController : it let me to switch between screens like a remotes
    val context = LocalContext.current
    val auth = FirebaseAuth.getInstance()
    var email by remember {mutableStateOf("")}
    var password by remember {mutableStateOf("")}
    var passwordVisibility by remember { mutableStateOf(false) }
    var message by remember {mutableStateOf("")}
    var isLoading by remember { mutableStateOf(false) }
    val activity = context as Activity
    val googleAuthHelper = remember { GoogleAuthHelper(activity) }
    val googleSignInClient = remember { googleAuthHelper.setupGoogleSignIn() }

    val launcher =
       /* this open google sign in screen */ rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            googleAuthHelper.handleSignInResult /* check sign in worked or not*/(
                result.data,
                onSuccess = { name ->
                    Toast.makeText(context, "Welcome $name", Toast.LENGTH_SHORT).show()
                    navController.navigate("home") {
                        popUpTo("login") { inclusive = true }
                    }
                },
                onFailure = { error ->
                    Toast.makeText(context, error, Toast.LENGTH_SHORT).show()
                }
            )
        }
        Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0B0C10)),
        contentAlignment = Alignment.Center
    ){
        Card(
            modifier = Modifier
                .fillMaxWidth(0.9f)
                .padding(top = 15.dp),

            shape = RoundedCornerShape(16.dp),
            CardDefaults.cardColors(containerColor = Color(0xFF101522))
        ){

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding( 30.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ){

                Text(
                    text = "FinSight",
                    fontSize = 28.sp,
                    color = Color(0xFF00BFFF),
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Welcome Back",
                    color = Color.White,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 14.dp),
                    textAlign = TextAlign.Center
                )
                Button(
                    onClick = {
                        val signInIntent = googleSignInClient.signInIntent
                        launcher.launch(signInIntent)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1E1E1E)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp),
                    shape = RoundedCornerShape(8.dp),
                    elevation = ButtonDefaults.elevatedButtonElevation(defaultElevation = 4.dp)
                ){
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.Center,
                        modifier = Modifier.fillMaxWidth()
                    ){
                        Icon(
                            painter = painterResource(id =R.drawable.google_logo),
                            contentDescription ="Google" ,
                            modifier = Modifier.size(24.dp)
                                .padding(end = 8.dp),
                            tint = Color.Unspecified
                        )
                        Text(
                            text = "Continue with Google",
                            color = Color.White,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Continue with Google" , color = Color.White)
                }
                Spacer(modifier  = Modifier.height(20.dp))
                Row(verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ){
                    Divider(
                        color = Color.Gray,
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        "  OR  ",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                    Divider(
                        color = Color.Gray,
                        modifier = Modifier.weight(1f)
                    )

                }
                Spacer(modifier = Modifier.height(20.dp))
                OutlinedTextField(value = email,
                    onValueChange = {email = it},
                    label = {Text("Email")},
                    singleLine = true ,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    modifier = Modifier.fillMaxWidth(),
                    leadingIcon = {
                        Icon(Icons.Default.Email, contentDescription = "Email Icon")
                    },
                            colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedBorderColor = Color(0xFF00BFFF),
                    unfocusedBorderColor = Color.Gray,
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                cursorColor = Color.White
                )
                )

                Spacer(modifier = Modifier.height(10.dp))

                OutlinedTextField(
                    value = password,
                    onValueChange = {password = it},
                    label = {Text("Enter password")},
                    singleLine = true,
                    visualTransformation = if(passwordVisibility) VisualTransformation.None else PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    modifier = Modifier.fillMaxWidth(),
                    leadingIcon = {
                        Icon(Icons.Default.Lock , contentDescription = "password")
                    },
                    trailingIcon = { // Icon on the right side
                        val image = if (passwordVisibility)
                            Icons.Filled.Visibility
                        else Icons.Filled.VisibilityOff

                        IconButton(onClick = { passwordVisibility = !passwordVisibility }) {
                            Icon(imageVector = image, contentDescription = "Toggle password visibility")
                        }
                    },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = Color.Transparent,
                        unfocusedContainerColor = Color.Transparent,
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        cursorColor = Color.White,
                        focusedBorderColor = Color(0xFF00BFFF),
                        unfocusedBorderColor = Color.Gray
                    )

                )
                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = {
                        if(email.isNotEmpty()&&password.isNotEmpty()){
                            isLoading = true
                            auth.signInWithEmailAndPassword(email,password)
                                .addOnCompleteListener { task->
                                    isLoading = false
                                    if(task.isSuccessful){
                                        Toast.makeText(context , "Login successfull" , Toast.LENGTH_SHORT).show()
                                        navController.navigate("home"){
                                            popUpTo("login"){inclusive = true}//prevent back nav
                                        }

                                    }
                                    else {
                                        Toast.makeText(context, "Login failed: ${task.exception?.message}", Toast.LENGTH_SHORT).show()
                                    }
                                }

                        }
                        else {
                            Toast.makeText(context, "Please enter all fields", Toast.LENGTH_SHORT).show()

                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp),
                    colors = ButtonDefaults.buttonColors(containerColor =Color(0xFF00BFFF)),
                     shape = RoundedCornerShape(10.dp)
                ) {
                    if(isLoading)
                        CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp)
                    else
                       Text("Login" , fontSize = 18.sp , color = Color.White  )
                }
                Spacer(modifier = Modifier.height(20.dp))
                Text(
                    text = "Don't have account ? Sign up"  ,
                    color = Color(0xFF808080),
                            fontSize = 16.sp,
                    modifier = Modifier.clickable {
                        navController.navigate("SignUp")
                    } )
            }
        }
    }

}