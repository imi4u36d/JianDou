export interface MaterialFavoriteCreateRequest {
  name: string;
  complete: () => void;
}

export interface MaterialFavoriteRenameRequest {
  folderId: string;
  name: string;
  complete: () => void;
}
