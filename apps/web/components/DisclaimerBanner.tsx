import React from "react";

export function DisclaimerBanner() {
  return (
    <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-6 rounded-r shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-3">
        <div className="flex-shrink-0 text-amber-700 font-bold">
          ⚠️ ESTIMATIVA NÃO OFICIAL
        </div>
        <p className="text-sm text-amber-800">
          Esta plataforma oferece estimativas independentes somente para provas com calibração disponível.
          As notas não constituem resultado oficial do INEP/MEC. A cobertura histórica e a validação científica
          ainda estão em desenvolvimento.
        </p>
      </div>
    </div>
  );
}
