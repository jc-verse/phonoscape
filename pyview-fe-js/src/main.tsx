import "@vitejs/plugin-react/preamble";

import React from "react";
import ReactDOM from "react-dom/client";

ReactDOM.hydrateRoot(
  document.getElementById("root")!,
  <React.StrictMode>
    <h1>It works!</h1>
  </React.StrictMode>,
);
