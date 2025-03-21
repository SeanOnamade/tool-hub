<template>
  <div class="p-6 max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-6 text-center">Tool Hub Aggregator</h1>
    
    <!-- Search Bar with Category Filter and AI Search Toggle -->
    <div class="flex flex-col md:flex-row md:items-center mb-6">
      <input
        v-model="searchQuery"
        @keyup.enter="searchTools"
        type="text"
        placeholder="Search by name or AI-powered..."
        class="flex-grow border border-gray-300 p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2 md:mb-0"
      />
      <input
        v-model="categoryQuery"
        @keyup.enter="searchTools"
        type="text"
        placeholder="Search by category..."
        class="flex-grow border border-gray-300 p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 md:ml-4"
      />
      <button
        @click="searchTools"
        class="ml-4 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
      >
        Search
      </button>
    </div>
    <!-- Toggle AI Search -->
    <div class="flex items-center mb-4">
      <input type="checkbox" v-model="useAISearch" id="ai-search-toggle" class="mr-2">
      <label for="ai-search-toggle" class="text-gray-700">Use AI-powered search</label>
    </div>

    <!-- List of Tools -->
    <ul>
      <li
        v-for="tool in tools"
        :key="tool.id"
        class="mb-4 p-4 border border-gray-200 rounded hover:shadow transition-shadow"
      >
        <!-- Use router-link to navigate to the details page -->
        <router-link :to="`/tools/${tool.id}`" class="text-xl font-semibold text-blue-600 hover:underline">
          {{ tool.name }}
        </router-link>
        <p class="text-gray-700 mt-2">{{ tool.description }}</p>
      </li>
    </ul>
  </div>
</template>
  
<script>
  import axios from "axios";
  
  export default {
    data() {
      return {
        tools: [],
        searchQuery: "",
        categoryQuery: "",
        useAISearch: false, // toggle
        timeout: null,
        lastQuery: "",
      };
    },
    watch: {
      searchQuery() {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
          this.searchTools();
        }, 500);
      },
      categoryQuery() {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
          this.searchTools();
        }, 500);
      },
    },
    created() {
      this.fetchTools();
    },
    methods: {
      fetchTools() {
        axios
          .get("http://localhost:8000/tools?skip=0&limit=10")
          .then((response) => {
            this.tools = response.data;
          })
          .catch((error) => {
            console.error("Error fetching tools:", error);
          });
        },
        searchTools() {
          if (this.searchQuery.trim() === "" && this.categoryQuery.trim() === "") {
            // empty, no search
            this.tools = []; // clear list
            this.fetchTools();
            return;
          }
          const params = new URLSearchParams();
          params.append("limit", "10");

          if (this.useAISearch && this.searchQuery.trim() !== "" && this.searchQuery !== this.lastQuery) {
            // AI Search 
            this.lastQuery = this.searchQuery;
            axios
              .get(`http://localhost:8000/tools/ai_search?q=${encodeURIComponent(this.searchQuery)}&top_k=10`)
              .then((response) => {
                this.tools = response.data;
              }) 
              .catch((error) => {
                console.error("Error with AI-powered search:", error);
              });
            } else {
              // Regular Search
              if (this.searchQuery.trim() !== "") {
                params.append("name", this.searchQuery);
              }
              if (this.categoryQuery.trim() !== "") {
                params.append("category", this.categoryQuery);
              }
              this.tools = [];
              axios
                .get(`http://localhost:8000/tools/search?${params.toString()}`)
                .then((response) => {
                  this.tools = response.data;
                })
                .catch((error) => {
                  console.error("Error searching tools:", error);
                });
          }
        },
    },
  };
  </script>
  