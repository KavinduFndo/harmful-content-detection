import { useEffect, useState } from "react";
import { listUsers } from "../api";
import type { User } from "../types";

export function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listUsers().then(setUsers).catch(() => setError("Only ADMIN can view users"));
  }, []);

  return (
    <div className="row" style={{ flexDirection: "column" }}>
      <h2>User Management</h2>
      {error && <div style={{ color: "#b91c1c" }}>{error}</div>}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.email}</td>
                <td>{u.role}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
