<template>
    <div class="search-results">
      <!-- <img alt="Vue logo" src="../assets/logo.png"> -->
      <Navbar />
      <SearchResults ref="search" v-bind:query="search_query" />
    </div>
  </template>
  
  <script>
  // @ is an alias to /src
  // import HelloWorld from '@/components/HelloWorld.vue'
  import Navbar from '@/components/Navbar.vue'
//   import Experiments from '@/components/Experiments.vue'
  import SearchResults from '@/components/SearchResults.vue'
  
  export default {
    name: 'SearchResultsView',
    props: ['search_query'],
    components: {
      Navbar,
      SearchResults,
   },
   methods:{
  
   },
  
  }
  </script>
  