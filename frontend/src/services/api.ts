import axios from 'axios';
import { showToast } from '../components/Toast';

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
            showToast(error.response.data.detail, 'error');
        } else if (error.response && error.response.status >= 500) {
            showToast("Erro interno do servidor. Tente novamente mais tarde.", 'error');
        } else if (!error.response) {
            showToast("Erro de conexão. Verifique sua rede.", 'error');
        } else {
            showToast("Um erro inesperado ocorreu. Tente novamente.", 'error');
        }
        return Promise.reject(error);
    }
);

export default api;
