const Redline = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 100 100"
    width="100%"
    height="100%"
    {...props}
  >
    <defs>
      <style>
        {
          "\n      .brand-red { fill: #d32f2f; }\n      .scale-white { fill: #ffffff; }\n      .scale-stroke { stroke: #ffffff; stroke-width: 0.8; stroke-linecap: round; }\n    "
        }
      </style>
    </defs>
    <path
      className="brand-red"
      fillRule="evenodd"
      stroke="#d32f2f"
      strokeWidth={2}
      strokeLinejoin="round"
      d="     M 22 15     H 62     C 87 15, 87 50, 62 50     L 82 85     H 57     L 42 50     V 85     H 22     Z     M 42 25     V 48     L 50 40     H 57     C 70 40, 70 25, 57 25     Z   "
    />
    <g
      style={{
        transformOrigin: "64px 71px",
        transform: "scale(0.75)",
      }}
    >
      <path className="scale-white" d="M63 64 h2 v13 h3 v1.5 h-8 v-1.5 h3 z" />
      <path className="scale-white" d="M55.5 64 h17 v1.5 h-17 z" />
      <path className="scale-white" d="M54 74 c0 2.5 4 2.5 4 0 z" />
      <path className="scale-white" d="M70 74 c0 2.5 4 2.5 4 0 z" />
      <g className="scale-stroke">
        <line x1={56} y1={65.5} x2={54} y2={74} />
        <line x1={56} y1={65.5} x2={58} y2={74} />
        <line x1={72} y1={65.5} x2={70} y2={74} />
        <line x1={72} y1={65.5} x2={74} y2={74} />
      </g>
    </g>
  </svg>
);
export default Redline;
