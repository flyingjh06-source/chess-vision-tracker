const io = require("socket.io-client");
const socket = io("https://chess-vision-tracker.onrender.com");

socket.on("connect", () => {
  console.log("Connected to server");
  socket.emit("create_room");
});

socket.on("room_created", (data) => {
  console.log("Room created:", data);
  socket.disconnect();
});

socket.on("connect_error", (err) => {
  console.log("Connection error:", err.message);
});
