<!-- <template>
  <img alt="Vue logo" src="./assets/logo.png">
  <HelloWorld msg="Welcome to Your Vue.js App"/>
</template> -->

<template>
  <!-- Simple navbar/header area -->
   <div>
    <header class="p-4 border-b flex justify-between items-center">
      <router-link to="/" class="text-2xl font-bold cursor-pointer">
        Tool Hub Aggregator
      </router-link>
      <div class="space-x-4">
        <!-- If user is not logged in, show Login button -->
        <button 
          v-if="!userProfile"
          @click="loginWithGoogle" 
          class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
        >
          Login with Google
        </button>

        <!-- If user is logged in, show Logout and Profile -->
        <button
          v-else
          @click="logout"
          class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded"
        >
          Logout
        </button>

        <button
          v-if="userProfile"
          @click="goToProfile"
          class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded"
        >
          Profile
        </button>
      </div>
    </header>

    <!-- Display user info if logged in -->
    <!-- <div v-if="userProfile" class="p-4 bg-gray-100">
      <p><strong>Logged in as:</strong> {{ userProfile.email }}</p>
      <p v-if="userProfile.name"><strong>Name:</strong> {{ userProfile.name }}</p>
      <img 
        v-if="userProfile.picture" 
        :src="userProfile.picture" 
        alt="Profile Picture" 
        class="w-16 h-16 rounded-full mt-2"
      />
    </div> -->

    <!-- Render whichever route we're on (ToolList, ToolDetails, etc.) -->
    <router-view />
  </div>
</template>

<script>
  // import ToolList from './components/ToolList.vue'
  import axios from "axios";

  export default {
  name: "App",
  data() {
    return {
      userProfile: null,
    };
  },
  created() {
    // Optionally, try to fetch profile on page load to see if user is already logged in
    this.fetchProfile();
  },
  methods: {
    loginWithGoogle() {
      window.location.href = "http://localhost:8000/auth/login";
    },
    fetchProfile() {
      axios
        .get("http://localhost:8000/auth/profile", { withCredentials: true })
        .then((res) => {
          this.userProfile = res.data;
        })
        .catch((error) => {
          console.error("Not logged in or error fetching profile:", error);
          this.userProfile = null;
        });
    },
    goToProfile() {
      // Navigate to /profile route
      this.$router.push("/profile");
    },
    logout() {
      axios
        .get("http://localhost:8000/auth/logout", { withCredentials: true })
        .then(() => {
          console.log("Logged out");
          this.userProfile = null; 
          // Redirect to homepage
          this.$router.push("/");
        })
        .catch((err) => {
          console.error("Logout error:", err);
        });
    },
  },
};
</script>


<!-- <script>
import HelloWorld from './components/HelloWorld.vue'

export default {
  name: 'App',
  components: {
    HelloWorld
  }
}
</script> -->

<!-- <style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

body {
  padding: 20px;
}
</style> -->
