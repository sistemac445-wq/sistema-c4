# Elegimos la imagen base
FROM node:18

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiamos archivos de dependencias
COPY package*.json ./
RUN npm install

# Copiamos el resto del código
COPY . .

# Exponemos el puerto que usa la app
EXPOSE 3000

# Comando para iniciar
CMD ["npm", "start"]