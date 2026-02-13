function data = mdp_FAlabels(data, varargin)
%MDP_FALABELS  - load data(1).FA.* labels
%
% usage examples: 
%
% load FA.WORDS (default)
% mview(...,'DPROC','mdp_FAlabels',...)
%
% load FA.PHONES
% mview(...,'DPROC',{{'mdp_FAlabels',{'PHONES'}}}, ...)
%
% add labels trajectory w/o mview
% data = mdp_FAlabels

% mkt 06/23

if isempty(varargin{1}),
	tier = 'WORDS';
else,
	tier = upper(varargin{1});
end;
if isfield(data,'FA'),
	p = data(1).FA.(tier);
	labs(length(p)) = struct('NAME',[],'OFFSET',[],'VALUE',[],'HOOK',[]);
	for k = 1 : length(p),
		labs(k).NAME = p(k).LABEL;
		labs(k).OFFSET = p(k).OFFSET(1)*1000;
	end;
	data(1).LABELS = labs;
end;
