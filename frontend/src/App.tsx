import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import Upload from "@/pages/Upload";
import Review from "@/pages/Review";
import Report from "@/pages/Report";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Upload />} />
          <Route path="/:policyId" element={<Upload />} />
          <Route path="/review/:policyId" element={<Review />} />
          <Route path="/report/:policyId" element={<Report />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
