<template>
    <div>
        <b-navbar toggleable="lg" type="dark" variant="info">
            <b-navbar-brand href="#">
                <img src="@/assets/logo-with-background.png" alt="braingeneers logo" class="d-inline-block align-top"
                    height=30px width=auto>
                <!-- <img src="https://placekitten.com/g/30/30" class="d-inline-block align-top" alt="Kitten"> -->
                BraingeneersHub
            </b-navbar-brand>
            <!-- <router-link to="/">Plates</router-link> | -->
            <router-link to="/experiments">Experiments</router-link> |
            <router-link to="/devices"> Devices</router-link>|
            <router-link to="/about"> About</router-link>

            <b-navbar-toggle target="nav-collapse"></b-navbar-toggle>
            <b-collapse id="nav-collapse" is-nav>
                <b-navbar-nav class="ml-auto">
                    <b-nav-form>
                        <b-form-input size="sm" class="mr-sm-2" placeholder="Search Experiments" v-model="search">
                        </b-form-input>
                        <b-button :disabled="search.length === 0" @click="redirectURL_for_search" size="sm"
                            class="my-2 my-sm-0" type="submit">Search</b-button>
                    </b-nav-form>
                    <b-nav-item-dropdown right>
                        <template v-slot:button-content>
                            <em>{{user.username}}</em>
                        </template>
                        <b-dropdown-item @click="openUserInfoModal" href="#">Profile</b-dropdown-item>
                        <b-dropdown-item @click="logout" href="#">Sign Out</b-dropdown-item>
                    </b-nav-item-dropdown>
                </b-navbar-nav>
            </b-collapse>
            <b-button style="display:none" id="user-info" v-b-modal="'user-info-modal'">user info</b-button>
            <b-modal size="lg" v-bind:id="'user-info-modal'" centered title="Profile Data">
                <div v-for="(value , name) in user" :key="name">
                    <!-- show data -->
                    <div class="row">
                        <div class="col-3">
                            {{name}}
                        </div>
                        <div class="col-9">
                            {{value}}
                        </div>
                    </div>
                </div>

            </b-modal>
        </b-navbar>
    </div>
</template>
<script>
import $ from 'jquery';

export default {
    name: 'NavBar',

    data() {
        return {
            username: "nobody",
            user: { "username": "user" },
            search: "",
        }
    },
    mounted() {
        // get user info fr
        // this.user = {"username": "user"};
        console.log("user")
        this.user = JSON.parse(window.localStorage.getItem('userData'));
        // console.log(this.user)
        // console.log("user", JSON.stringify(this.user, 0, 2));
    },

    methods:
    {

        clicked() {
            console.log("clicked")
        },
        loadUserInfo() {
            // get user info from local storage
            this.user = JSON.parse(window.localStorage.getItem('userData'));
            console.log("user", JSON.stringify(this.user, 0, 2));
        },
        openUserInfoModal() {
            this.user = JSON.parse(window.localStorage.getItem('userData'));
            // console.log(this.user)
            console.log("user", JSON.stringify(this.user, 0, 2));
            // console.log("openUserInfoModal")
            $('#user-info').click()
        },
        logout() {
            window.localStorage.removeItem("jwt");
            window.localStorage.removeItem("userData");
            this.user = { "username": "user" }
            this.$auth.isAuthenticated = false;
            this.$auth.logout({
                returnTo: window.location.origin + "/datahub"
            });
        },
        // logout() {
        //     window.localStorage.removeItem("jwt");
        //     window.localStorage.removeItem("userData");
        //     this.$router.push("/");
        // },
        redirectURL_for_search() {
            this.$router.push("/search/" + this.search);
        }
    },
}

</script>
<style>

</style>