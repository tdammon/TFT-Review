import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import { Auth0Provider } from "@auth0/auth0-react";
import { BrowserRouter } from "react-router-dom";
import AppRoutes from "./AppRoutes";

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);

const domain = process.env.REACT_APP_AUTH0_DOMAIN;
const clientId = process.env.REACT_APP_AUTH0_CLIENT_ID;
const audience = process.env.REACT_APP_AUTH0_AUDIENCE;
if (!domain || !clientId) {
  throw new Error("Missing Auth0 configuration. Check your .env file.");
}

root.render(
  <React.StrictMode>
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: audience,
        scope: "openid profile email offline_access",
      }}
      useRefreshTokens={true}
      cacheLocation="localstorage"
    >
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </Auth0Provider>
  </React.StrictMode>
);
