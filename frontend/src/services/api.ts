import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

console.log('API Base URL:', api.defaults.baseURL);


export default api;
