<template>
        <div>
            <Navbar />
            <div class="flex items-center justify-center h-screen">
                <div class="sm:w-1/2">
                    <div class="p-5 w-4/5 mx-auto text-left font-raleway">
                        <div class="text-left mb-7">
                            <router-link to="/">
                                HOME
                            </router-link> 
                        </div>
                        <h4>
                            Sign Up.
                        </h4>
                        <p v-show="error" class="text-sm text-red-500">{{ errorMsg }}</p>
                        <form @submit="register">
                                <h4>Name</h4>
                                <input type="text" v-model="name" class="text-sm outline-none pb-2 w-4/5 bg-transparent border-b hover:border-blue-700 focus:border-blue-700">


                                <h4 class="text-left font-bold mb-2 font-montserrat">Email</h4>
                                <input type="email" v-model="email" class="text-sm outline-none pb-2 w-4/5 bg-transparent border-b hover:border-blue-700 focus:border-blue-700">


                                <h4 class="text-left font-bold mb-2 font-montserrat">Password</h4>
                                <input type="password" v-model="password" class="text-sm outline-none pb-2 w-4/5 bg-transparent border-b hover:border-blue-700 focus:border-blue-700">


                                <h4 class="text-left font-bold mb-2 font-montserrat">Username</h4>
                                <input type="text" v-model="username" class="text-sm outline-none pb-2 w-4/5 bg-transparent border-b hover:border-blue-700 focus:border-blue-700">

                            
                            <button type="submit" :disabled="name.length < 6 || password.length < 6 || username.length < 3">
                                Sign Up 
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

</template>
<script>
    import Navbar from '@/components/Navbar.vue'
    import axios from 'axios'

    export default {
        name: 'Register',
        data() {
            return {
                name: '',
                email: '',
                password: '',
                username: '',
                error: false,
                errorMsg: `An Error occurred, please try again`
            }
        },
        components: {
            Navbar
        },
        methods: {
            // createUser(){
            //     console.log("create sample")
            //     console.log(this.form.sample_name)
            //     console.log(this.form.sample_description)
            //     console.log(well_id)
            //     // post with api_token
            //     axios.post('http://localhost:1337/api/samples', {
            //         data:{
            //             name: this.form.sample_name,
            //             description: this.form.sample_description,
            //             well: well_id
            //         }
            //     }, {
            //         headers: {
            //             'Authorization': `Bearer ${this.api_token}`
            //         }
            //     })
            //     .then(response => {
            //         console.log(response);
            //     })
            //     .catch(function (error) {
            //         console.log(error);
            //     });
            // },
            async register(e) {
                try {
                    e.preventDefault()
                        await axios.post(`http://localhost:1337/api/auth/local/register`, {
                        name: this.name,
                        password: this.password,
                        email: this.email,
                        username: this.username
                    })
                    this.$router.push('/')
                } catch(e) {
                    console.log(e)
                    this.error = true
                    this.email = ''
                } 
            }
        }
    }
</script>
<!-- <style scoped>
</style> -->