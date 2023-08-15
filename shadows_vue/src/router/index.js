import Vue from 'vue'
import VueRouter from 'vue-router'
import PlatesView from '../views/PlatesView.vue'
import WellsView from '../views/WellsView.vue'
import ExperimentsView from '../views/ExperimentsView.vue'
import Register from '../views/Register.vue'
import Login from '../views/Login.vue'
import SearchResultsView from '../views/SearchResultsView.vue'
import DevicesView from '../views/DevicesView.vue'
import LoginRedirect from '../views/LoginRedirect.vue'

Vue.use(VueRouter)
// /* eslint-disable */
const routes = [
    {
        path: '/',
        name: 'Login',
        component: Login,
        meta: {
            title: 'Login - Braingeneers Hub',
            metaTags: [
                {
                    name: 'description',
                    content: 'login page'
                },
                {
                    property: 'og:description',
                    content: 'login'
                }
            ]
        }
    },
    {
        path: '/register',
        name: 'Register',
        component: Register
    },

    {
        path: '/plates',
        name: 'plates',
        component: PlatesView,
        props: true,
        meta: {
            title: 'Experiments - Braingeneers Hub',
            metaTags: [
                {
                    name: 'description',
                    content: 'experiments page'
                },
                {
                    property: 'og:description',
                    content: 'experiments page'
                }
            ]
        }
    },
    {
        path: '/wells/:plate_name_from_url',
        name: 'wells',
        component: WellsView,
        props: true,
        meta: {
            title: 'Wells - Braingeneers Hub',
            metaTags: [
                {
                    name: 'description',
                    content: 'view wells'
                },
                {
                    property: 'og:description',
                    content: 'wells page'
                }
            ]
        }
    },
    {
        path: '/wells',
        name: 'all_wells',
        component: WellsView,
        meta: {
            title: 'Wells - Braingeneers Hub',
            metaTags: [
                {
                    name: 'description',
                    content: 'view wells'
                },
                {
                    property: 'og:description',
                    content: 'wells page'
                }
            ]
        }
    },

    {
        path: '/experiments',
        name: 'experiments',
        component: ExperimentsView,
        meta: {
            title: 'Experiments - Braingeneers Hub',
            metaTags: [
                {
                    name: 'description',
                    content: 'experiments page'
                },
                {
                    property: 'og:description',
                    content: 'experiments page'
                }
            ]
        }
    },
    {
        path: '/devices',
        name: 'devices',
        component: DevicesView,
        meta: {
            title: 'Devices - Braingeneers Hub',
            metaTags: [
                {
                    name: 'description',
                    content: 'devices page'
                },
                {
                    property: 'og:description',
                    content: 'devices page'
                }
            ]
        }
    },
    {
        path: '/search/:search_query',
        name: 'search',
        props: true,
        component: SearchResultsView,
        meta: {
            title: 'Search - Braingeneers Hub',
            metaTags: [
                {
                    name: 'description',
                    content: 'experiment search page'
                },
                {
                    property: 'og:description',
                    content: 'experiments search page'
                }
            ]
        }
    },
    {
        path: '/auth',
        name: 'auth',
        beforeEnter() { location.href = `${process.env.VUE_APP_API_ENDPOINT}/api/connect/auth0` },

    },
    {
        path: '/connect/auth0/redirect',
        name: 'login-redirect',
        component: LoginRedirect,

        props: route => ({ IDToken: route.query.id_token, access_token: route.query.access_token })
    },
    {
        path: '/about',
        name: 'about',
        // route level code-splitting
        // this generates a separate chunk (about.[hash].js) for this route
        // which is lazy-loaded when the route is visited.
        component: () => import(/* webpackChunkName: "about" */ '../views/AboutView.vue')
    }
]

// const router = new VueRouter({
//   routes
// })
const router = new VueRouter({
    mode: 'history',
    base: '/datahub/',
    // base: process.env.VUE_APP_BASE_URL,
    routes
})

export default router


// ... 

// This callback runs before every route change, including on page load.
router.beforeEach((to, from, next) => {
    // This goes through the matched routes from last to first, finding the closest route with a title.
    // e.g., if we have `/some/deep/nested/route` and `/some`, `/deep`, and `/nested` have titles,
    // `/nested`'s will be chosen.
    const nearestWithTitle = to.matched.slice().reverse().find(r => r.meta && r.meta.title);

    // Find the nearest route element with meta tags.
    const nearestWithMeta = to.matched.slice().reverse().find(r => r.meta && r.meta.metaTags);

    const previousNearestWithMeta = from.matched.slice().reverse().find(r => r.meta && r.meta.metaTags);

    // If a route with a title was found, set the document (page) title to that value.
    if (nearestWithTitle) {
        document.title = nearestWithTitle.meta.title;
    } else if (previousNearestWithMeta) {
        document.title = previousNearestWithMeta.meta.title;
    }

    // Remove any stale meta tags from the document using the key attribute we set below.
    Array.from(document.querySelectorAll('[data-vue-router-controlled]')).map(el => el.parentNode.removeChild(el));

    // Skip rendering meta tags if there are none.
    if (!nearestWithMeta) return next();

    // Turn the meta tag definitions into actual elements in the head.
    nearestWithMeta.meta.metaTags.map(tagDef => {
        const tag = document.createElement('meta');

        Object.keys(tagDef).forEach(key => {
            tag.setAttribute(key, tagDef[key]);
        });

        // We use this to track which meta tags we create so we don't interfere with other ones.
        tag.setAttribute('data-vue-router-controlled', '');

        return tag;
    })
        // Add the meta tags to the document head.
        .forEach(tag => document.head.appendChild(tag));

    next();
});

  // ...