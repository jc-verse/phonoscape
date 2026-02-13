function data = mdp_flip(data, varargin)
%MDP_FLIP  - MVIEW dataproc that inverts the specified dimension(s) of specified signals
%
% by default applies to 3rd dimension of all multi-dimensional signals
%
% usage examples: 
%
% flip 3rd dimension of all multi-dimensional signals within data
% mview(...,'DPROC','mdp_flip',...)
%
% flip 1st dimension of all multi-dimensional signals within data
% mview(...,'DPROC',{{'mdp_flip',{[] ,1}}},...)
%
% to flip dimension 3 of TT
% mview(...,'DPROC',{{'mdp_flip',{'TT'}}}, ...)
%
% to flip dimensions 1 and 3 of TT and TD
% mview(...,'DPROC',{{'mdp_flip',{{'TT','TD'},[1 3]}}}, ...)
%
% to specify other DPROCs
% mview(...,'DPROC',{'mdp_LipAperture',{'mdp_flip',{{'LA',1}}}}, ...)

% mkt 03/09

sensors = [];
dims = 3;
if length(varargin) > 1,	% last arg is {pal,phar,labs}
	args = varargin(1:length(varargin)-1);
end;
if length(args) > 1,
	sensors = args{1};
	dims = args{2};
else
	sensors = args{1};
end
if ischar(sensors), sensors = {sensors}; end

for k = 1 : length(data),
	if size(data(k).SIGNAL,2) < 2, continue; end
	if isempty(sensors) || ~isempty((k==find(strcmpi(data(k).NAME,sensors)))),
		data(k).SIGNAL(:,dims) = -data(k).SIGNAL(:,dims);
	end
end;
