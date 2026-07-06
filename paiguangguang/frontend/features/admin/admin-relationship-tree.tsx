"use client";

type TreeNode = {
  label: string;
  value?: string;
  children: TreeNode[];
};

function insertPath(root: TreeNode[], segments: string[], fullValue: string) {
  if (segments.length === 0) {
    return;
  }

  let level = root;
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    const isLeaf = index === segments.length - 1;
    let node = level.find((entry) => entry.label === segment && entry.value === (isLeaf ? fullValue : undefined));
    if (!node) {
      node = {
        label: segment,
        value: isLeaf ? fullValue : undefined,
        children: [],
      };
      level.push(node);
    }
    level = node.children;
  }
}

function buildTree(values: string[], delimiter: string | null) {
  const root: TreeNode[] = [];

  values
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right))
    .forEach((value) => {
      const segments = delimiter ? value.split(delimiter).filter(Boolean) : [value];
      insertPath(root, segments, value);
    });

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((left, right) => left.label.localeCompare(right.label));
    nodes.forEach((node) => sortNodes(node.children));
  };

  sortNodes(root);
  return root;
}

function TreeBranch({
  node,
  depth,
  selectedValues,
  onToggle,
}: {
  node: TreeNode;
  depth: number;
  selectedValues: string[];
  onToggle: (value: string) => void;
}) {
  const value = node.value;

  if (value !== undefined) {
    const checked = selectedValues.includes(value);
    return (
      <label className="flex items-start gap-3 py-2" style={{ paddingLeft: `${depth * 1.1}rem` }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={() => onToggle(value)}
          className="mt-1 h-4 w-4 border-ink/30 text-tide focus:ring-tide/20"
        />
        <span className="text-sm text-ink">{node.label}</span>
        <span className="text-xs text-ink/45">{value}</span>
      </label>
    );
  }

  return (
    <div className="py-2" style={{ paddingLeft: `${depth * 1.1}rem` }}>
      <div className="text-xs font-semibold uppercase tracking-wide text-clay">{node.label}</div>
      <div className="mt-1 space-y-0.5">
        {node.children.map((child) => (
          <TreeBranch
            key={`${node.label}:${child.value ?? child.label}`}
            node={child}
            depth={depth + 1}
            selectedValues={selectedValues}
            onToggle={onToggle}
          />
        ))}
      </div>
    </div>
  );
}

export function AdminRelationshipTree({
  title,
  description,
  values,
  selectedValues,
  onChange,
  delimiter,
  emptyMessage = "No values available.",
}: {
  title: string;
  description?: string;
  values: string[];
  selectedValues: string[];
  onChange: (values: string[]) => void;
  delimiter: string | null;
  emptyMessage?: string;
}) {
  const tree = buildTree(values, delimiter);

  function toggle(value: string) {
    if (selectedValues.includes(value)) {
      onChange(selectedValues.filter((entry) => entry !== value));
      return;
    }
    onChange([...selectedValues, value].sort((left, right) => left.localeCompare(right)));
  }

  return (
    <div className="border border-ink/10 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold uppercase tracking-wide text-clay">{title}</h4>
          {description ? <p className="mt-2 text-sm leading-6 text-ink/70">{description}</p> : null}
        </div>
        <span className="border border-ink/15 bg-paper px-2.5 py-1 text-xs font-semibold text-ink">
          {selectedValues.length} selected
        </span>
      </div>

      <div className="mt-4 border border-ink/10 bg-paper/60 p-3">
        {tree.length === 0 ? (
          <div className="text-sm text-ink/60">{emptyMessage}</div>
        ) : (
          <div className="space-y-0.5">
            {tree.map((node) => (
              <TreeBranch
                key={node.value ?? node.label}
                node={node}
                depth={0}
                selectedValues={selectedValues}
                onToggle={toggle}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
