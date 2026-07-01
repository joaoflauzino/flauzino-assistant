import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.data && error.response.data.detail) {
            alert(`Erro: ${error.response.data.detail}`);
        } else {
            alert("Um erro inesperado ocorreu. Tente novamente.");
        }
        return Promise.reject(error);
    }
);

console.log('API Base URL:', api.defaults.baseURL);

export default api;
