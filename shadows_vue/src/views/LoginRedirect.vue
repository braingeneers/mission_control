<!-- a vue component to handle redirect authentication with strapi -->
<template>
    <div>
        <h1>Redirecting...</h1>
        <!-- login button -->
        <button @click="login">Login</button>
        <button @click="logout">Logout</button>
        <a href="https://dev-zp88n4zn.us.auth0.com/v2/logout" @click="logout"> Logout  tryyasfdg</a>
    </div>
</template>

<script>
import axios from 'axios';

export default {
    name: "LoginRedirect",
    props: ["access_token", "IDToken"],
    data() {
        return {
            username: "nobody",
            user: { "username": "user" },
            search: "",
        }
    },
    async mounted() {
        console.log("?id_token=" + this.IDToken)
        console.log("access_token=" + this.access_token)
        // console.log(this.thing)
        //get jwt from strapi with GET
        await axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/auth/auth0/callback?id_token=${this.IDToken}&access_token=${this.access_token}`).then(res => {
                    console.log(res);
                    const { jwt, user } = res.data;
                    console.log(jwt);
                    console.log(user);
                    //if successful, set this.$auth.isAuthenticated = true
                    this.$auth.isAuthenticated = true;
                    // console.log(this.password);
                    // console.log(this.email);
                    window.localStorage.setItem("jwt", jwt);
                    window.localStorage.setItem("userData", JSON.stringify(user));

                    // window.localStorage.setItem('bookmarks', JSON.stringify(user.bookmarks))
                    //emit user
                    // this.$emit('user', user)
                    this.$router.push("/experiments");
                });


    },

    methods:
    {
        async login(e) {
            e.preventDefault();
            try {

                await axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/auth/auth0/callback?id_token=${this.IDToken}&access_token=${this.access_token}`).then(res => {
                    console.log(res);
                    const { jwt, user } = res.data;
                    console.log(jwt);
                    console.log(user);
                    // console.log(this.password);
                    // console.log(this.email);
                    window.localStorage.setItem("jwt", jwt);
                    window.localStorage.setItem("userData", JSON.stringify(user));
                    // window.localStorage.setItem('bookmarks', JSON.stringify(user.bookmarks))
                    //emit user
                    // this.$emit('user', user)
                    this.$router.push("/experiments");
                });

            }
            catch (error) {
                console.log(error);
                this.error = true;
                this.password = "";
            }
        },
        logout() {
            window.localStorage.removeItem("jwt");
            window.localStorage.removeItem("userData");
            this.$auth.logout({
                returnTo: window.location.origin
            });
        },
    },
}
</script>