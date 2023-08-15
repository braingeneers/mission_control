<template>
    <button
      class="btn btn-primary btn-block"
      v-if="!$auth.isAuthenticated"
      @click="login"
    >
      Log In
    </button>
  </template>
  
  <script>
    export default {
      name: 'LoginButton',
      methods: {
        login() {
          this.$auth.loginWithRedirect({
            "redirect_uri":`${process.env.VUE_APP_API_ENDPOINT}/api/connect/auth0/callback`,
            "audience" : "http://strapi-shadows-auth0-API"})
        },
      },
    };
  </script>