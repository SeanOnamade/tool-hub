<template>
    <div class="p-6 max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-6">User Profile</h1>
  
      <div v-if="profile">
        <p><strong>Email:</strong> {{ profile.email }}</p>
        <p><strong>Name:</strong> {{ profile.name }}</p>
        <img 
          v-if="profile.picture" 
          :src="profile.picture" 
          alt="Profile Picture"
          class="w-16 h-16 rounded-full mt-2"
        />
      </div>
      <div v-else>
        <p>Loading or not logged in</p>
      </div>
    </div>
  </template>
  
  <script>
  import axios from "axios";
  
  export default {
    name: "ProfilePage",
    data() {
      return {
        profile: null
      };
    },
    created() {
      // Fetch user profile on component load
      axios
        .get("http://localhost:8000/auth/profile", { withCredentials: true })
        .then((res) => {
          this.profile = res.data;
        })
        .catch((err) => {
          console.error("Error fetching profile:", err);
          // If user not logged in, or error, we might redirect to home
          // this.$router.push('/')
        });
    }
  };
  </script>
  