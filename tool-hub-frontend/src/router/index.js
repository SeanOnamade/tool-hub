import {createRouter, createWebHistory} from 'vue-router';
import ToolList from '../components/ToolList.vue';
import ToolDetails from '../components/ToolDetails.vue';
import ProfilePage from '../components/ProfilePage.vue';

const routes = [
    {
        path: '/',
        name: 'ToolList',
        component: ToolList,
    },
    {
        path: '/tools/:id',
        name: 'ToolDetails',
        component: ToolDetails,
        props: true,
    },
    {
        path: '/profile',
        name: 'Profile',
        component: ProfilePage,
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

export default router;