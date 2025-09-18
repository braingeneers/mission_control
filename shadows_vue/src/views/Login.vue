<template>
    <div class="home">
        <img alt="Vue logo" src="../assets/logo.png" />

        <!-- Check that the SDK client is not currently loading before accessing is methods -->
        <div v-if="!$auth.loading">
            <!-- show login when not authenticated -->
            <button v-if="!$auth.isAuthenticated" @click="login">Log in</button>
            <!-- show logout when authenticated -->
            <button v-if="$auth.isAuthenticated" @click="logout">Log out</button>
        </div>
    </div>
</template>

<script>
// import axios from 'axios'
// import { useAuth0 } from '@auth0/auth0-vue';
// import LoginButton from '@/components/LoginButton';

export default {
    name: "Login",
    // components: { LoginButton },
    data() {
        return {
            email: "",
            password: "",
            error: false,
            errorMsg: `An error occurred, please try again`,
        };
    },
    async mounted(){
        var token = window.localStorage.getItem('jwt');
        console.log("token", token)
        // eslint-disable-next-line no-constant-condition
        if (true){
            this.$router.push("/experiments");
        } else{
            // beforeEnter() { location.href = `${process.env.VUE_APP_API_ENDPOINT}/api/connect/auth0` }
            //set one second timeout to allow auth0 to load
            setTimeout(() => {
                this.$auth.loginWithRedirect({
                    redirect_uri: `${process.env.VUE_APP_API_AUTH_ENDPOINT}/api/connect/auth0`,  
                });
            }, 1000);


            // await this.$auth.loginWithRedirect({
            //     redirect_uri: `${process.env.VUE_APP_API_ENDPOINT}/api/connect/auth0`,
            // });
        }

    },
    // setup() {
    //     const { loginWithRedirect } = useAuth0();

    //     return {
    //         logine: () => {
    //             loginWithRedirect();
    //         }
    //     };
    // },
    methods: {
        // Log the user in
        login() {
            this.$auth.loginWithRedirect({
                redirect_uri: `${process.env.VUE_APP_API_AUTH_ENDPOINT}/api/connect/auth0`,
            });
        },
        // Log the user out
        logout() {
            this.$auth.logout({
                returnTo: window.location.origin
            });
        }
        // async login(e) {
        //     e.preventDefault();
        //     try {
        //         const res = await axios.post(`${process.env.VUE_APP_API_ENDPOINT}/api/auth/local`, {
        //             identifier: this.email,
        //             password: this.password
        //         });
        //         const { jwt, user } = res.data;

        //         // console.log(this.password);
        //         // console.log(this.email);
        //         window.localStorage.setItem("jwt", jwt);
        //         window.localStorage.setItem("userData", JSON.stringify(user));
        //         // window.localStorage.setItem('bookmarks', JSON.stringify(user.bookmarks))
        //         //emit user
        //         // this.$emit('user', user)
        //         this.$router.push("/experiments");
        //     }
        //     catch (error) {
        //         console.log(error);
        //         this.error = true;
        //         this.password = "";
        //     }
        // },
        // logout() {
        //     window.localStorage.removeItem("jwt");
        //     window.localStorage.removeItem("userData");
        //     this.$router.push("/");
        // },
    },
}
</script>
<style scoped lang="css">
.body {
    display: flex;
    padding-top: 60px;
    padding-bottom: 600px;
    align-items: center;
    background-color: #f3f2fe;
}

.form-signin {
    width: 100%;
    max-width: 450px;
    margin: auto;
}

label {
    font-weight: 600;
}

.responsive {
    width: 100%;
    height: auto;
    /* padding-top: 5px;
        padding-right: 0;
        padding-left: 0; */
}
</style>
<!-- <style scoped>
    
</style> -->
